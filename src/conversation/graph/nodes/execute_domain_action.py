"""Implementation of the execute_domain_action conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    _BOOKING_REQUEST_CLEANUP_FIELDS,
    Action,
    BookingResponseObject,
    BookingStatus,
    ConversationState,
    DomainOperation,
    ExpectedInteraction,
    ExpectedInteractionKind,
    InformationField,
    Intent,
    MatchResponse,
    StateUpdate,
    _booking_availability_signature,
    _fields_for_data_request,
    _information_removals,
    _is_valid_domain_result,
    _safe_error_response,
    _safe_log_exception,
)


def execute_domain_action(
    context: ConversationNodeContext,
    state: ConversationState,
) -> StateUpdate:
    """Delegate a selected operation and retain only its result in state."""

    operation = state.get("domain_operation")

    if not isinstance(operation, DomainOperation):
        response = _safe_error_response(
            context.user_interaction,
            reason="No valid domain operation was selected",
        )
        return {
            "domain_operation": None,
            "response": response,
            "response_in_domain_language": response.text,
            "session_active": response.session_active,
            "last_intent_fulfilled": False,
        }

    try:
        result = context.domain_adapter.execute(
            operation=operation,
            information=state.get(
                "collected_information",
                {},
            ),
        )
        if not _is_valid_domain_result(operation, result):
            raise TypeError(f"Invalid result for domain operation {operation.value}")
    except Exception as error:  # noqa: BLE001
        _safe_log_exception(
            f"Domain operation {operation.value} failed",
            error,
        )
        response = _safe_error_response(
            context.user_interaction,
            reason=f"Domain operation {operation.value} failed",
        )

        return {
            "domain_operation": None,
            "response": response,
            "response_in_domain_language": response.text,
            "session_active": response.session_active,
            "last_intent_fulfilled": False,
        }

    if operation in {
        DomainOperation.PREVIEW_BOOKING,
        DomainOperation.CREATE_BOOKING,
    } and isinstance(result, MatchResponse):
        updates: StateUpdate = {
            "domain_operation": None,
            "domain_data": result,
            "action": Action.DISPLAY_AVAILABILITY,
            "expected_interaction": None,
            "last_intent_fulfilled": True,
        }
        return updates

    if operation == DomainOperation.CHECK_BOOKING_AVAILABILITY:
        if not isinstance(result, MatchResponse):
            response = _safe_error_response(
                context.user_interaction,
                reason="Invalid early availability result",
            )
            return {
                "domain_operation": None,
                "response": response,
                "response_in_domain_language": response.text,
                "session_active": response.session_active,
                "last_intent_fulfilled": False,
            }

        if not result.rooms:
            return {
                "domain_operation": None,
                "domain_data": result,
                "action": Action.DISPLAY_AVAILABILITY,
                "expected_interaction": None,
                "last_intent_fulfilled": True,
                "validated_availability_signature": None,
            }

        requested_field = state.get("next_missing_field")
        if not isinstance(requested_field, InformationField):
            response = _safe_error_response(
                context.user_interaction,
                reason="Early availability check has no requested field",
            )
            return {
                "domain_operation": None,
                "response": response,
                "response_in_domain_language": response.text,
                "session_active": response.session_active,
                "last_intent_fulfilled": False,
            }

        return {
            "domain_operation": None,
            "domain_data": _fields_for_data_request(
                state,
                requested_field,
            ),
            "action": Action.ASK_FOR_DATA,
            "last_intent_fulfilled": False,
            "validated_availability_signature": (
                _booking_availability_signature(state.get("collected_information", {}))
            ),
        }

    if operation == DomainOperation.PREVIEW_BOOKING:
        expected = ExpectedInteraction(
            kind=ExpectedInteractionKind.BOOKING_CONFIRMATION,
            intent=Intent.BOOKING_REQUEST,
            operation=DomainOperation.CREATE_BOOKING,
        )

        return {
            "domain_operation": None,
            "domain_data": result,
            "action": Action.ASK_FOR_CONFIRMATION,
            "expected_interaction": expected,
            "last_intent_fulfilled": False,
        }

    if (
        operation == DomainOperation.GET_BOOKING
        and state.get("current_intent") == Intent.BOOKING_CANCELLATION
    ):
        if result is None:
            return {
                "domain_operation": None,
                "domain_data": None,
                "action": Action.DISPLAY_BOOKING,
                "last_intent_fulfilled": False,
            }

        if (
            isinstance(result, BookingResponseObject)
            and result.status == BookingStatus.CANCELLED
        ):
            return {
                "domain_operation": None,
                "domain_data": result,
                "action": Action.DISPLAY_BOOKING,
                "expected_interaction": None,
                "last_intent_fulfilled": True,
            }

        expected = ExpectedInteraction(
            kind=ExpectedInteractionKind.CANCELLATION_CONFIRMATION,
            intent=Intent.BOOKING_CANCELLATION,
            operation=DomainOperation.CANCEL_BOOKING,
        )

        return {
            "domain_operation": None,
            "domain_data": result,
            "action": Action.ASK_FOR_CONFIRMATION,
            "expected_interaction": expected,
            "last_intent_fulfilled": False,
        }

    response_action = {
        DomainOperation.FIND_AVAILABILITY: Action.DISPLAY_AVAILABILITY,
        DomainOperation.GET_BOOKING: Action.DISPLAY_BOOKING,
        DomainOperation.CREATE_BOOKING: Action.DISPLAY_BOOKING,
        DomainOperation.CANCEL_BOOKING: Action.DISPLAY_BOOKING,
        DomainOperation.GET_INFORMATION: Action.DISPLAY_INFO,
        DomainOperation.PREVIEW_BOOKING: Action.DISPLAY_BOOKING,
    }[operation]

    updates = {
        "domain_operation": None,
        "domain_data": result,
        "action": response_action,
        "last_intent_fulfilled": True,
    }

    if operation == DomainOperation.FIND_AVAILABILITY:
        updates["availability_requested"] = True
    elif operation == DomainOperation.CREATE_BOOKING:
        updates["collected_information"] = _information_removals(
            _BOOKING_REQUEST_CLEANUP_FIELDS
        )
        updates["validated_availability_signature"] = None
    elif operation == DomainOperation.GET_INFORMATION:
        updates["collected_information"] = _information_removals(
            {InformationField.INFORMATION_TOPIC}
        )

    return updates


__all__ = ["execute_domain_action"]
