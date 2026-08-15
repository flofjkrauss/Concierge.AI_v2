"""Implementation of the begin_turn conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    ConversationState,
    Intent,
    StateUpdate,
    _is_usable_message,
    _is_valid_interaction_response,
    _safe_error_response,
    _safe_log_exception,
)


def begin_turn(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Initialize a thread or normalize transient fields for a new turn."""

    updates: StateUpdate = {
        "parsed_message": None,
        "translated_message": None,
        "detected_intent": None,
        "extracted_information": [],
        "original_message_extracted_fields": [],
        "changed_fields": [],
        "action": None,
        "domain_operation": None,
        "domain_data": None,
        "response": None,
        "response_in_domain_language": None,
        "confirmation_outcome": None,
        "termination_requested": False,
    }

    if not state.get("initialized", False):
        session_id = state.get("session_id")
        if not isinstance(session_id, str) or not session_id.strip():
            response = _safe_error_response(
                context.user_interaction,
                reason="A new conversation requires a valid session ID",
            )
            updates.update(
                {
                    "response": response,
                    "response_in_domain_language": response.text,
                    "session_active": response.session_active,
                }
            )
            return updates

        init_intent = Intent.CONVERSATION_INITIATION
        try:
            response = context.user_interaction.display_greeting(
                intent=init_intent,
                data=session_id,
            )
            if not _is_valid_interaction_response(response):
                raise TypeError("Greeting construction returned an invalid response")
        except Exception as error:  # noqa: BLE001
            _safe_log_exception("Greeting construction failed", error)
            response = _safe_error_response(
                context.user_interaction,
                reason="Greeting construction failed",
            )

        updates.update(
            {
                "initialized": True,
                "session_active": True,
                "language": state.get("language"),
                "message_history": [],
                "collected_information": {},
                "current_intent": init_intent,
                "last_intent_fulfilled": False,
                "missing_fields": [],
                "unknown_counter": 0,
                "expected_interaction": None,
                "pending_information_changes": {},
                "next_missing_field": None,
                "availability_requested": False,
                "last_booking_check_in": None,
                "validated_availability_signature": None,
                "response": response,
                "response_in_domain_language": response.text,
            }
        )
        return updates

    raw_message = state.get("incoming_message")

    if raw_message is not None and not isinstance(raw_message, str):
        error_response = _safe_error_response(
            context.user_interaction,
            reason="Invalid message type",
        )
        updates.update(
            {
                "response": error_response,
                "response_in_domain_language": error_response.text,
                "session_active": error_response.session_active,
            }
        )
        return updates

    try:
        is_empty_message = raw_message is None or not raw_message.strip()
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Message validation failed", error)
        error_response = _safe_error_response(
            context.user_interaction,
            reason="Invalid message",
        )
        updates.update(
            {
                "response": error_response,
                "response_in_domain_language": error_response.text,
                "session_active": error_response.session_active,
            }
        )
        return updates

    if is_empty_message:
        try:
            empty_response = context.user_interaction.send_empty_response()
            if not _is_valid_interaction_response(empty_response):
                raise TypeError(
                    "Empty response construction returned an invalid response"
                )
        except Exception as error:  # noqa: BLE001
            _safe_log_exception("Empty response construction failed", error)
            empty_response = _safe_error_response(
                context.user_interaction,
                reason="Empty response construction failed",
            )

        updates.update(
            {
                "response": empty_response,
                "response_in_domain_language": empty_response.text,
                "session_active": empty_response.session_active,
            }
        )
        return updates

    try:
        parsed_message = context.user_interaction.parse_message(
            raw_message=raw_message,
        )
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Message parsing failed", error)
        parsed_message = None

    if not _is_usable_message(parsed_message):
        error_response = _safe_error_response(
            context.user_interaction,
            reason="Invalid message",
        )

        updates.update(
            {
                "response": error_response,
                "response_in_domain_language": error_response.text,
                "session_active": error_response.session_active,
            }
        )
        return updates

    updates["parsed_message"] = parsed_message
    return updates


__all__ = ["begin_turn"]
