"""Implementation of the translate_response conversation graph node."""

from __future__ import annotations

import re

from conversation.entities.interaction_response import InformationResponse

from .context import ConversationNodeContext
from .support import (
    ConversationState,
    InteractionResponse,
    Message,
    StateUpdate,
    _is_usable_message,
    _safe_log_exception,
    _safe_log_warning,
    replace,
)

_INFORMATION_WIRE_PATTERN = re.compile(
    r"^\((?P<topic>[a-z][a-z0-9_]*)\)(?P<answer>.+)$",
    flags=re.DOTALL,
)
_SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def translate_response(
    context: ConversationNodeContext,
    state: ConversationState,
) -> StateUpdate:
    """Translate a response copy into the session language."""

    response = state.get("response")

    if (
        not isinstance(response, InteractionResponse)
        or not isinstance(response.text, str)
        or not response.text
    ):
        return {}

    session_language = state.get("language") or context.domain_language

    if session_language == context.domain_language:
        return {}

    source_text = response.text
    information_topic: str | None = None
    if isinstance(response, InformationResponse):
        information_match = _INFORMATION_WIRE_PATTERN.fullmatch(source_text)
        if information_match is not None:
            information_topic = information_match.group("topic")
            source_text = information_match.group("answer")

    translated_parts: list[str] = []
    for source_part in _SENTENCE_BOUNDARY_PATTERN.split(source_text):
        try:
            translated = context.translator.translate(
                Message(content=source_part),
                target_lang=session_language,
                source_lang=context.domain_language,
            )
        except Exception as error:  # noqa: BLE001
            _safe_log_exception("Response translation failed", error)
            return {}

        if not _is_usable_message(translated):
            _safe_log_warning("Translator returned an invalid response translation")
            return {}

        translated_parts.append(translated.content)

    translated_text = " ".join(translated_parts)
    if information_topic is not None:
        translated_text = f"({information_topic}){translated_text}"

    return {
        "response": replace(
            response,
            text=translated_text,
        )
    }


__all__ = ["translate_response"]
