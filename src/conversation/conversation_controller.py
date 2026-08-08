"""Thin facade around the compiled LangGraph conversation workflow."""

from collections.abc import Mapping
from typing import Protocol, cast
from uuid import uuid4

from conversation.entities.interaction_response import InteractionResponse
from conversation.graph.builder import ConversationGraph
from conversation.graph.state import ConversationInput, ConversationOutput
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
    ) -> None:
        self._graph = graph
        self._user_interaction = user_interaction

    def init_conversation(self) -> InteractionResponse:
        """Create and initialize a new in-memory LangGraph thread."""

        session_id = str(uuid4())
        result = self._graph.invoke(
            ConversationInput(
                session_id=session_id,
                session_active=True,
                language=None,
                incoming_message=None,
            ),
            self._config(session_id),
        )
        LOG_MSG.debug(f"Conversation initiated. Session ID: {session_id}")
        return self._response_from(result)

    def process_message(
        self,
        session_id: str,
        message: str,
    ) -> InteractionResponse:
        """Process one message in the checkpoint selected by ``session_id``."""
        
        snapshot = cast(
            StateSnapshot,
            self._graph.get_state(self._config(session_id)),
        )
        if not snapshot.values:
            return self._user_interaction.send_error_msg(
                reason="Session not found",
            )
        if snapshot.values.get("session_active") is not True:
            return self._user_interaction.send_error_msg(
                reason="Session is not active",
            )
        
        result = self._graph.invoke(
            ConversationInput(incoming_message=message),
            self._config(session_id),
        )
        LOG_MSG.debug(f"Message processed: {result}")
        return self._response_from(result)


    @staticmethod
    def _config(session_id: str) -> dict[str, object]:
        return {"configurable": {"thread_id": session_id}}

    def _response_from(
        self,
        result: ConversationOutput,
    ) -> InteractionResponse:
        response = result.get("response")
        if isinstance(response, InteractionResponse):
            return response
        return self._user_interaction.send_error_msg(
            reason="Conversation graph returned no response",
        )
