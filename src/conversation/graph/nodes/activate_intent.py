"""Implementation of the activate_intent conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    Action,
    ConversationState,
    InformationField,
    Intent,
    IntentInformationMapper,
    StateUpdate,
    _is_valid_information,
    _open_requested_fields,
)


def activate_intent(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    detected = state.get("detected_intent") or Intent.UNKNOWN
    current = state.get(
        "current_intent",
        Intent.CONVERSATION_INITIATION,
    )
    changed_fields = set(state.get("changed_fields", []))

    requested_fields = _open_requested_fields(state)
    extracted_fields = {
        information.information_field
        for information in state.get("extracted_information", [])
    }

    if requested_fields & extracted_fields:
        return {
            "current_intent": current,
            "last_intent_fulfilled": False,
        }

    if detected == Intent.UNKNOWN and extracted_fields == {
        InformationField.INFORMATION_TOPIC
    }:
        return {
            "current_intent": Intent.INFORMATION_REQUEST,
            "last_intent_fulfilled": False,
        }

    if detected == Intent.CONVERSATION_INITIATION:
        return {
            "action": Action.DISPLAY_GREETING,
            "domain_data": state.get("session_id"),
        }

    if detected != Intent.UNKNOWN:
        intent_updates: StateUpdate = {
            "current_intent": detected,
            "last_intent_fulfilled": False,
        }
        starts_new_intent = current != detected or state.get(
            "last_intent_fulfilled",
            False,
        )

        if detected == Intent.AVAILABILITY_CHECK and starts_new_intent:
            intent_updates.update(
                {
                    "availability_requested": False,
                    "validated_availability_signature": None,
                }
            )

        if detected in {
            Intent.BOOKING_CHECK,
            Intent.BOOKING_CANCELLATION,
        } and starts_new_intent:
            last_booking_check_in = state.get("last_booking_check_in")
            if (
                InformationField.CHECK_IN not in extracted_fields
                and _is_valid_information(last_booking_check_in)
            ):
                intent_updates["collected_information"] = {
                    InformationField.CHECK_IN: last_booking_check_in
                }

        if detected == Intent.BOOKING_REQUEST and (
            current != Intent.BOOKING_REQUEST
            or state.get("last_intent_fulfilled", False)
        ):
            intent_updates["validated_availability_signature"] = None
        return intent_updates

    relevant_fields = set(
        IntentInformationMapper.determine_fields(
            intent=current,
        )
    )

    current_is_open = not state.get(
        "last_intent_fulfilled",
        False,
    )

    if current_is_open or bool((changed_fields | extracted_fields) & relevant_fields):
        return {
            "current_intent": current,
            "last_intent_fulfilled": False,
        }

    return {
        "action": Action.ASK_INTENT,
        "domain_data": None,
    }


__all__ = ["activate_intent"]
