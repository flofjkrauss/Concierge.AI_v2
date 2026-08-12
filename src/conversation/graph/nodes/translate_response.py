"""Implementation of the translate_response conversation graph node."""

from __future__ import annotations

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

    try:
        translated = context.translator.translate(
            Message(content=response.text),
            target_lang=session_language,
            source_lang=context.domain_language,
        )
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Response translation failed", error)
        return {}

    if not _is_usable_message(translated):
        _safe_log_warning("Translator returned an invalid response translation")
        return {}

    return {
        "response": replace(
            response,
            text=translated.content,
        )
    }


__all__ = ["translate_response"]
