"""Implementation of the resolve_confirmation conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    _BOOKING_REQUEST_CLEANUP_FIELDS,
    Action,
    ConfirmationOutcome,
    ConversationState,
    ExpectedInteractionKind,
    Intent,
    IntentInformationMapper,
    StateUpdate,
    _confirmation_decision,
    _information_change_data,
    _information_removals,
    _plausible_information,
    _required_message,
)


def resolve_confirmation(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Interpret a reply only when an explicit confirmation is pending."""

    expected = state.get("expected_interaction")

    if expected is None:
        raise ValueError("No confirmation is pending")

    message = _required_message(state, "translated_message")
    decision = _confirmation_decision(message.content)

    if expected.kind == ExpectedInteractionKind.INFORMATION_CHANGE_CONFIRMATION:
        pending_changes = dict(state.get("pending_information_changes", {}))

        if decision is True:
            return {
                "collected_information": pending_changes,
                "pending_information_changes": {},
                "expected_interaction": None,
                "current_intent": expected.intent,
                "last_intent_fulfilled": False,
                "confirmation_outcome": (
                    ConfirmationOutcome.INFORMATION_CHANGE_CONFIRMED
                ),
            }

        if decision is False:
            existing_information = state.get("collected_information", {})
            additions = {
                field: information
                for field, information in pending_changes.items()
                if field not in existing_information
            }
            explicit_revisions = {
                information.information_field: information
                for information in state.get(
                    "extracted_information",
                    [],
                )
                if (
                    information.information_field
                    in IntentInformationMapper.determine_fields(expected.intent)
                    and information.information_field in existing_information
                    and existing_information[information.information_field].content
                    != information.content
                )
            }
            accepted_changes = additions | explicit_revisions
            valid_changes, _ = _plausible_information(
                list(accepted_changes.values()),
                existing_information,
            )
            decline_updates: StateUpdate = {
                "pending_information_changes": {},
                "expected_interaction": None,
                "current_intent": expected.intent,
                "last_intent_fulfilled": False,
                "confirmation_outcome": (
                    ConfirmationOutcome.INFORMATION_CHANGE_DECLINED
                ),
            }
            if valid_changes:
                decline_updates["collected_information"] = {
                    information.information_field: information
                    for information in valid_changes
                }
            return decline_updates

        detected_intent = state.get("detected_intent") or Intent.UNKNOWN

        if detected_intent not in {
            Intent.UNKNOWN,
            expected.intent,
        }:
            return {
                "pending_information_changes": {},
                "expected_interaction": None,
                "confirmation_outcome": ConfirmationOutcome.INTERRUPTED,
            }

        return {
            "action": Action.ASK_FOR_INFORMATION_CHANGE,
            "domain_data": _information_change_data(
                state.get("collected_information", {}),
                pending_changes,
            ),
            "confirmation_outcome": ConfirmationOutcome.UNCLEAR,
        }

    changed_fields = set(state.get("changed_fields", []))

    required_fields = set(
        IntentInformationMapper.determine_fields(
            intent=expected.intent,
        )
    )

    if changed_fields & required_fields:
        return {
            "expected_interaction": None,
            "current_intent": expected.intent,
            "last_intent_fulfilled": False,
            "confirmation_outcome": ConfirmationOutcome.CHANGED,
        }

    if decision is True:
        if expected.operation is None:
            raise ValueError("Operation confirmation requires a domain operation")

        return {
            "expected_interaction": None,
            "current_intent": expected.intent,
            "domain_operation": expected.operation,
            "confirmation_outcome": ConfirmationOutcome.CONFIRMED,
        }

    if decision is False:
        operation_decline_updates: StateUpdate = {
            "expected_interaction": None,
            "current_intent": expected.intent,
            "last_intent_fulfilled": True,
            "action": Action.CONFIRMATION_DECLINED,
            "domain_operation": None,
            "domain_data": None,
            "confirmation_outcome": ConfirmationOutcome.DECLINED,
        }

        if expected.intent == Intent.BOOKING_REQUEST:
            operation_decline_updates["collected_information"] = _information_removals(
                _BOOKING_REQUEST_CLEANUP_FIELDS
            )
            operation_decline_updates["validated_availability_signature"] = None

        return operation_decline_updates

    detected_intent = state.get("detected_intent") or Intent.UNKNOWN

    if detected_intent not in {
        Intent.UNKNOWN,
        expected.intent,
    }:
        return {
            "expected_interaction": None,
            "confirmation_outcome": ConfirmationOutcome.INTERRUPTED,
        }

    return {
        "action": Action.ASK_FOR_CONFIRMATION,
        "domain_data": dict(state.get("collected_information", {})),
        "confirmation_outcome": ConfirmationOutcome.UNCLEAR,
    }


__all__ = ["resolve_confirmation"]
