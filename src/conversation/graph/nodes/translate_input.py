"""Implementation of the translate_input conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    BookingSelection,
    ConversationState,
    Information,
    InformationField,
    StateUpdate,
    _is_usable_message,
    _required_message,
    _safe_log_exception,
    _safe_log_warning,
    _valid_language_or_default,
    replace,
)


def translate_input(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Detect the session language once and translate input to English."""

    parsed_message = _required_message(state, "parsed_message")
    session_language = state.get("language")

    if BookingSelection.from_wire(parsed_message.content) is not None:
        if not isinstance(session_language, str) or not session_language.strip():
            session_language = context.domain_language
        normalized = replace(
            parsed_message,
            original_content=(
                parsed_message.original_content or parsed_message.content
            ),
            language=session_language,
        )
        return {
            "collected_information": {
                InformationField.PREFERRED_LANG: Information(
                    information_field=InformationField.PREFERRED_LANG,
                    content=session_language,
                ),
            },
            "language": session_language,
            "translated_message": normalized,
        }

    if session_language is None:
        try:
            detected_language = context.translator.determine(parsed_message)
            session_language = _valid_language_or_default(
                detected_language,
                context.domain_language,
            )
        except Exception as error:  # noqa: BLE001
            _safe_log_exception("Language detection failed", error)
            session_language = context.domain_language
    elif not isinstance(session_language, str) or not session_language.strip():
        session_language = context.domain_language

    translated = parsed_message

    if session_language != context.domain_language:
        try:
            candidate = context.translator.translate(
                parsed_message,
                target_lang=context.domain_language,
                source_lang=session_language,
            )
            if _is_usable_message(candidate):
                translated = candidate
            else:
                _safe_log_warning("Translator returned an invalid input translation")
        except Exception as error:  # noqa: BLE001
            _safe_log_exception("Input translation failed", error)

    normalized = replace(
        translated,
        original_content=(parsed_message.original_content or parsed_message.content),
        language=session_language,
    )

    preferred_language = Information(
        information_field=InformationField.PREFERRED_LANG,
        content=session_language,
    )

    return {
        "collected_information": {
            InformationField.PREFERRED_LANG: preferred_language,
        },
        "language": session_language,
        "translated_message": normalized,
    }


__all__ = ["translate_input"]
