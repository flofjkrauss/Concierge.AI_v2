"""Implementation of the determine_action conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    Action,
    ConversationState,
    DomainOperation,
    Intent,
    StateUpdate,
    _booking_availability_signature,
    _fields_for_data_request,
)


def determine_action(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Select a response action or domain operation deterministically."""

    current_intent = state.get(
        "current_intent",
        Intent.CONVERSATION_INITIATION,
    )

    missing_fields = state.get("missing_fields", [])

    if missing_fields:
        requested_field = state.get("next_missing_field")
        if requested_field not in missing_fields:
            requested_field = missing_fields[0]

        availability_signature = _booking_availability_signature(
            state.get("collected_information", {})
        )
        if (
            current_intent == Intent.BOOKING_REQUEST
            and availability_signature is not None
            and availability_signature != state.get("validated_availability_signature")
        ):
            return {
                "domain_operation": (DomainOperation.CHECK_BOOKING_AVAILABILITY),
                "next_missing_field": requested_field,
                "last_intent_fulfilled": False,
            }

        return {
            "action": Action.ASK_FOR_DATA,
            "domain_data": _fields_for_data_request(
                state,
                requested_field,
            ),
            "next_missing_field": requested_field,
            "last_intent_fulfilled": False,
        }

    operation_by_intent = {
        Intent.AVAILABILITY_CHECK: DomainOperation.FIND_AVAILABILITY,
        Intent.BOOKING_CHECK: DomainOperation.GET_BOOKING,
        Intent.INFORMATION_REQUEST: DomainOperation.GET_INFORMATION,
        Intent.BOOKING_CANCELLATION: DomainOperation.GET_BOOKING,
    }

    operation = operation_by_intent.get(current_intent)

    if operation is not None:
        return {
            "domain_operation": operation,
        }

    if current_intent == Intent.BOOKING_REQUEST:
        return {
            "domain_operation": DomainOperation.PREVIEW_BOOKING,
            "last_intent_fulfilled": False,
        }

    return {
        "action": Action.ASK_INTENT,
        "domain_data": None,
    }


__all__ = ["determine_action"]
