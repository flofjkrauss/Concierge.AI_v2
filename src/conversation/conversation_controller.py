"""Thin facade around the compiled LangGraph conversation workflow."""

from collections.abc import Mapping
from typing import Protocol, cast
from uuid import uuid4

from configuration.application import ApplicationSettings
from conversation.entities.interaction_response import (
    ErrorResponse,
    InteractionResponse,
)
from conversation.entities.message import Message
from conversation.graph.builder import ConversationGraph
from conversation.graph.state import ConversationInput, ConversationOutput
from conversation.models.translation.interface import TranslatorInterface
from conversation.user_interaction import UserInteraction
from observability.log_messages import LOG_MSG


class StateSnapshot(Protocol):
    """Subset of LangGraph's checkpoint snapshot used by this facade."""

    values: Mapping[str, object]


class ConversationController:
    """Create thread IDs, invoke the graph, and return conversation responses."""

    def __init__(
        self,
        graph: ConversationGraph,
        user_interaction: UserInteraction,
        translator: TranslatorInterface | None = None,
    ) -> None:
        self._graph = graph
        self._user_interaction = user_interaction
        self._translator = translator
        settings = ApplicationSettings.get_settings()
        self._domain_language = settings.domain_language
        self._message_max_length = settings.msg_max_length

    def init_conversation(self) -> InteractionResponse:
        """Create and initialize a new in-memory LangGraph thread."""

        session_id = str(uuid4())
        try:
            result = self._graph.invoke(
                ConversationInput(
                    session_id=session_id,
                    session_active=True,
                    language=None,
                    incoming_message=None,
                ),
                self._config(session_id),
            )
        except Exception as error:  # noqa: BLE001
            self._log_failure("Conversation initialization failed", error)
            return self._safe_error_response(
                reason="Conversation initialization failed"
            )

        self._safe_debug(f"Conversation initiated. Session ID: {session_id}")
        return self._response_from(result)

    def process_message(
        self,
        session_id: str,
        message: str,
    ) -> InteractionResponse:
        """Process one message in the checkpoint selected by ``session_id``."""

        if not self._is_safe_text(session_id, require_content=True):
            return self._safe_error_response(reason="Invalid session ID")
        if not self._is_safe_text(message):
            return self._safe_error_response(reason="Invalid message")

        try:
            snapshot = cast(
                StateSnapshot,
                self._graph.get_state(self._config(session_id)),
            )
        except Exception as error:  # noqa: BLE001
            self._log_failure("Conversation state lookup failed", error)
            return self._safe_error_response(
                reason="Conversation state lookup failed"
            )

        if not snapshot.values:
            return self._safe_error_response(reason="Session not found")
        if snapshot.values.get("session_active") is not True:
            return self._safe_error_response(reason="Session is not active")

        try:
            result = self._graph.invoke(
                ConversationInput(incoming_message=message),
                self._config(session_id),
            )
        except Exception as error:  # noqa: BLE001
            self._log_failure("Conversation message processing failed", error)
            return self._safe_error_response(
                reason="Conversation message processing failed"
            )

        self._safe_debug(f"Conversation message processed: {session_id}")
        return self._response_from(result)

    def terminate_conversation(self, session_id: str) -> None:
        """Mark one known conversation inactive without invoking the NLP flow."""

        if not self._is_safe_text(session_id, require_content=True):
            return

        config = self._config(session_id)
        try:
            snapshot = cast(StateSnapshot, self._graph.get_state(config))
            if not snapshot.values:
                return
            if snapshot.values.get("session_active") is not False:
                self._graph.update_state(
                    config,
                    {
                        "session_active": False,
                        "expected_interaction": None,
                        "pending_information_changes": {},
                    },
                )
        except Exception as error:  # noqa: BLE001
            self._log_failure("Conversation termination failed", error)
            return

        self._safe_debug(f"Conversation terminated. Session ID: {session_id}")

    def patience_response(
        self,
        session_id: str,
        message: str,
    ) -> InteractionResponse:
        """Return a fixed progress message in the current session language."""

        source_text = "Thank you for your patience. I need just another moment."
        if not self._is_safe_text(session_id, require_content=True):
            return InteractionResponse(session_active=True, text=source_text)

        language: str | None = None
        session_active = True
        try:
            snapshot = cast(
                StateSnapshot,
                self._graph.get_state(self._config(session_id)),
            )
            stored_language = snapshot.values.get("language")
            if isinstance(stored_language, str) and stored_language.strip():
                language = stored_language
            stored_session_active = snapshot.values.get("session_active")
            if isinstance(stored_session_active, bool):
                session_active = stored_session_active
        except Exception as error:  # noqa: BLE001
            self._log_failure("Patience-message state lookup failed", error)

        if (
            language is None
            and self._translator is not None
            and self._is_safe_text(message, require_content=True)
            and len(message) <= self._message_max_length
        ):
            try:
                detected = self._translator.determine(Message(content=message))
                if isinstance(detected, str) and detected.strip():
                    language = detected.strip()
            except Exception as error:  # noqa: BLE001
                self._log_failure("Patience-message language detection failed", error)

        if (
            language is not None
            and language != self._domain_language
            and self._translator is not None
        ):
            try:
                translated = self._translator.translate(
                    Message(content=source_text),
                    target_lang=language,
                    source_lang=self._domain_language,
                )
                if self._is_safe_text(translated.content, require_content=True):
                    source_text = translated.content
            except Exception as error:  # noqa: BLE001
                self._log_failure("Patience-message translation failed", error)

        return InteractionResponse(
            session_active=session_active,
            text=source_text,
        )

    @staticmethod
    def _config(session_id: str) -> dict[str, object]:
        return {"configurable": {"thread_id": session_id}}

    def _response_from(
        self,
        result: ConversationOutput | object,
    ) -> InteractionResponse:
        response = result.get("response") if isinstance(result, Mapping) else None
        if isinstance(response, InteractionResponse):
            return response
        return self._safe_error_response(
            reason="Conversation graph returned no response"
        )

    def _safe_error_response(
        self,
        *,
        reason: str,
        session_active: bool = True,
    ) -> ErrorResponse:
        try:
            response = self._user_interaction.send_error_msg(
                reason=reason,
                session_active=session_active,
            )
            if isinstance(response, ErrorResponse):
                return response
        except Exception as error:  # noqa: BLE001
            self._log_failure("Error response construction failed", error)

        return ErrorResponse(
            text="Something went terribly wrong!",
            session_active=session_active,
            reason=reason,
        )

    @staticmethod
    def _log_failure(message: str, error: Exception) -> None:
        try:
            LOG_MSG.error(f"{message} ({type(error).__name__})")
        except Exception:  # noqa: BLE001, S110
            pass

    @staticmethod
    def _safe_debug(message: str) -> None:
        try:
            LOG_MSG.debug(message)
        except Exception:  # noqa: BLE001, S110
            pass

    @staticmethod
    def _is_safe_text(value: object, *, require_content: bool = False) -> bool:
        if not isinstance(value, str):
            return False
        try:
            value.encode("utf-8")
            return not require_content or bool(value.strip())
        except Exception:  # noqa: BLE001
            return False
