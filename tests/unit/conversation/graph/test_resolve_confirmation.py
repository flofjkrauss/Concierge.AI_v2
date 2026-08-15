"""Focused tests for information-change confirmation branches."""

from types import SimpleNamespace
from typing import cast

import pytest

from conversation.entities.information import Information
from conversation.graph.nodes.context import ConversationNodeContext
from conversation.graph.nodes.resolve_confirmation import resolve_confirmation
from conversation.graph.state import (
    ConfirmationOutcome,
    ConversationState,
    DomainOperation,
    ExpectedInteraction,
    ExpectedInteractionKind,
)
from conversation.value_object.action import Action
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


def _context() -> ConversationNodeContext:
    return cast(ConversationNodeContext, SimpleNamespace())


def _state(**values: object) -> ConversationState:
    return cast(ConversationState, values)


def _expected() -> ExpectedInteraction:
    return ExpectedInteraction(
        kind=ExpectedInteractionKind.INFORMATION_CHANGE_CONFIRMATION,
        intent=Intent.BOOKING_REQUEST,
        operation=None,
    )


def test_information_change_accepts_pending_values() -> None:
    replacement = Information(InformationField.LAST_NAME, "Doe")

    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_expected(),
            extracted_information=[Information(InformationField.CONFIRMATION, "yes")],
            pending_information_changes={InformationField.LAST_NAME: replacement},
        ),
    )

    assert result["confirmation_outcome"] is (
        ConfirmationOutcome.INFORMATION_CHANGE_CONFIRMED
    )
    assert result["collected_information"] == {
        InformationField.LAST_NAME: replacement
    }


def test_unclear_information_change_repeats_change_prompt() -> None:
    replacement = Information(InformationField.LAST_NAME, "Doe")

    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_expected(),
            extracted_information=[],
            pending_information_changes={InformationField.LAST_NAME: replacement},
            collected_information={},
            detected_intent=Intent.UNKNOWN,
        ),
    )

    assert result["action"] is Action.ASK_FOR_INFORMATION_CHANGE
    assert result["confirmation_outcome"] is ConfirmationOutcome.UNCLEAR


def test_information_change_can_be_interrupted_by_new_intent() -> None:
    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_expected(),
            extracted_information=[],
            pending_information_changes={},
            detected_intent=Intent.INFORMATION_REQUEST,
        ),
    )

    assert result == {
        "pending_information_changes": {},
        "expected_interaction": None,
        "confirmation_outcome": ConfirmationOutcome.INTERRUPTED,
    }


def test_resolve_confirmation_requires_pending_interaction() -> None:
    with pytest.raises(ValueError, match="No confirmation is pending"):
        resolve_confirmation(_context(), _state())


def test_declined_information_change_keeps_only_new_valid_information() -> None:
    email = Information(InformationField.EMAIL, "alex@example.com")
    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_expected(),
            extracted_information=[Information(InformationField.CONFIRMATION, "no")],
            pending_information_changes={InformationField.EMAIL: email},
            collected_information={},
        ),
    )

    assert result["confirmation_outcome"] is (
        ConfirmationOutcome.INFORMATION_CHANGE_DECLINED
    )
    assert result["collected_information"] == {InformationField.EMAIL: email}


def _operation_confirmation(
    operation: DomainOperation | None = DomainOperation.CREATE_BOOKING,
) -> ExpectedInteraction:
    return ExpectedInteraction(
        kind=ExpectedInteractionKind.BOOKING_CONFIRMATION,
        intent=Intent.BOOKING_REQUEST,
        operation=operation,
    )


def test_changed_required_field_invalidates_pending_confirmation() -> None:
    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_operation_confirmation(),
            changed_fields=[InformationField.EMAIL],
        ),
    )

    assert result["confirmation_outcome"] is ConfirmationOutcome.CHANGED
    assert result["expected_interaction"] is None


def test_confirmed_operation_is_selected_for_execution() -> None:
    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_operation_confirmation(),
            extracted_information=[Information(InformationField.CONFIRMATION, "yes")],
        ),
    )

    assert result["domain_operation"] is DomainOperation.CREATE_BOOKING
    assert result["confirmation_outcome"] is ConfirmationOutcome.CONFIRMED


def test_operation_confirmation_requires_operation() -> None:
    with pytest.raises(ValueError, match="requires a domain operation"):
        resolve_confirmation(
            _context(),
            _state(
                expected_interaction=_operation_confirmation(None),
                extracted_information=[
                    Information(InformationField.CONFIRMATION, "yes")
                ],
            ),
        )


def test_declined_booking_confirmation_resets_booking_progress() -> None:
    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_operation_confirmation(),
            extracted_information=[Information(InformationField.CONFIRMATION, "no")],
        ),
    )

    assert result["action"] is Action.CONFIRMATION_DECLINED
    assert result["confirmation_outcome"] is ConfirmationOutcome.DECLINED
    assert result["availability_requested"] is False
    assert result["missing_fields"] == []


@pytest.mark.parametrize(
    ("detected_intent", "expected_outcome"),
    [
        (Intent.INFORMATION_REQUEST, ConfirmationOutcome.INTERRUPTED),
        (Intent.UNKNOWN, ConfirmationOutcome.UNCLEAR),
    ],
)
def test_unclear_operation_confirmation_can_repeat_or_be_interrupted(
    detected_intent: Intent,
    expected_outcome: ConfirmationOutcome,
) -> None:
    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_operation_confirmation(),
            extracted_information=[],
            detected_intent=detected_intent,
            collected_information={},
        ),
    )

    assert result["confirmation_outcome"] is expected_outcome
    if expected_outcome is ConfirmationOutcome.UNCLEAR:
        assert result["action"] is Action.ASK_FOR_CONFIRMATION
    else:
        assert result["expected_interaction"] is None
