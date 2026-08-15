"""Focused branch tests for graph domain-operation execution."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

from conversation.entities.information import Information
from conversation.entities.interaction_response import (
    BookingResponseObject,
)
from conversation.graph.nodes.context import ConversationNodeContext
from conversation.graph.nodes.execute_domain_action import execute_domain_action
from conversation.graph.state import ConversationState, DomainOperation
from conversation.user_interaction import UserInteraction
from conversation.value_object.action import Action
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent
from domain.entities.room import Room
from domain.services.create_customer import EmailAlreadyInUseError
from domain.services.find_matching_rooms import MatchResponse
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.money import Money


def _context(adapter: Mock) -> ConversationNodeContext:
    return cast(
        ConversationNodeContext,
        SimpleNamespace(
            domain_adapter=adapter,
            user_interaction=UserInteraction(),
        ),
    )


def _state(**values: object) -> ConversationState:
    return cast(ConversationState, values)


def _booking_object(status: BookingStatus) -> BookingResponseObject:
    return BookingResponseObject(
        status=status,
        room_category="double",
        guest_count=2,
        check_in=date(2030, 6, 10),
        check_out=date(2030, 6, 13),
        total_prize=Money(Decimal("300.00"), "EUR"),
        accessible=False,
        breakfast=False,
        first_name="Alex",
        last_name="Morgan",
        email="alex@example.com",
    )


def test_email_conflict_selects_explicit_guest_response() -> None:
    adapter = Mock()
    adapter.execute.side_effect = EmailAlreadyInUseError("duplicate")

    result = execute_domain_action(
        _context(adapter),
        _state(
            domain_operation=DomainOperation.CREATE_BOOKING,
            collected_information={},
        ),
    )

    assert result["action"] is Action.REPORT_EMAIL_IN_USE
    assert result["availability_requested"] is False


def test_booking_preview_requests_confirmation() -> None:
    adapter = Mock()
    preview = BookingResponseObject(
        status=BookingStatus.PENDING,
        room_category="double",
        guest_count=2,
        check_in=date(2030, 6, 10),
        check_out=date(2030, 6, 13),
        total_prize=Money(Decimal("300.00"), "EUR"),
        accessible=False,
        breakfast=False,
        first_name="Alex",
        last_name="Morgan",
        email="alex@example.com",
    )
    adapter.execute.return_value = preview

    result = execute_domain_action(
        _context(adapter),
        _state(
            domain_operation=DomainOperation.PREVIEW_BOOKING,
            collected_information={},
        ),
    )

    assert result["action"] is Action.ASK_FOR_CONFIRMATION
    assert result["domain_data"] is preview


def test_cancelled_booking_lookup_does_not_request_confirmation() -> None:
    adapter = Mock()
    booking = _booking_object(BookingStatus.CANCELLED)
    adapter.execute.return_value = booking

    result = execute_domain_action(
        _context(adapter),
        _state(
            domain_operation=DomainOperation.GET_BOOKING,
            current_intent=Intent.BOOKING_CANCELLATION,
            collected_information={},
        ),
    )

    assert result["action"] is Action.DISPLAY_BOOKING
    assert result["last_intent_fulfilled"] is True
    assert result["last_booking_check_in"].content == booking.check_in  # type: ignore[union-attr]


def test_information_result_removes_consumed_topic() -> None:
    adapter = Mock(return_value=None)
    adapter.execute.return_value = "(wifi)Free Wi-Fi"

    result = execute_domain_action(
        _context(adapter),
        _state(
            domain_operation=DomainOperation.GET_INFORMATION,
            collected_information={},
        ),
    )

    assert result["action"] is Action.DISPLAY_INFO
    assert result["collected_information"] == {
        InformationField.INFORMATION_TOPIC: None
    }


def test_missing_domain_operation_returns_safe_error() -> None:
    adapter = Mock()

    result = execute_domain_action(_context(adapter), _state())

    adapter.execute.assert_not_called()
    assert result["last_intent_fulfilled"] is False
    assert "response" in result


def test_invalid_domain_result_returns_safe_error() -> None:
    adapter = Mock()
    adapter.execute.return_value = object()

    result = execute_domain_action(
        _context(adapter),
        _state(domain_operation=DomainOperation.GET_INFORMATION),
    )

    assert result["last_intent_fulfilled"] is False
    assert result["collected_information"] == {
        InformationField.INFORMATION_TOPIC: None
    }


def test_failed_booking_creation_invalidates_previous_availability() -> None:
    adapter = Mock()
    adapter.execute.side_effect = RuntimeError("database unavailable")

    result = execute_domain_action(
        _context(adapter),
        _state(domain_operation=DomainOperation.CREATE_BOOKING),
    )

    assert result["availability_requested"] is False
    assert result["validated_availability_signature"] is None
    assert result["last_intent_fulfilled"] is False


def test_early_availability_without_rooms_displays_result() -> None:
    adapter = Mock()
    no_rooms = MatchResponse(None, [])  # type: ignore[arg-type]
    adapter.execute.return_value = no_rooms

    result = execute_domain_action(
        _context(adapter),
        _state(domain_operation=DomainOperation.CHECK_BOOKING_AVAILABILITY),
    )

    assert result["action"] is Action.DISPLAY_AVAILABILITY
    assert result["domain_data"] is no_rooms
    assert result["availability_requested"] is False


def test_early_availability_requests_room_category_when_rooms_exist(
    room: Room,
) -> None:
    adapter = Mock()
    rooms = MatchResponse(None, [room])  # type: ignore[arg-type]
    adapter.execute.return_value = rooms
    information = {
        InformationField.CHECK_IN: Information(
            InformationField.CHECK_IN,
            date(2030, 6, 10),
        ),
        InformationField.CHECK_OUT: Information(
            InformationField.CHECK_OUT,
            date(2030, 6, 13),
        ),
    }

    result = execute_domain_action(
        _context(adapter),
        _state(
            domain_operation=DomainOperation.CHECK_BOOKING_AVAILABILITY,
            next_missing_field=InformationField.ROOM_CATEGORY,
            collected_information=information,
        ),
    )

    assert result["action"] is Action.DISPLAY_AVAILABILITY
    assert result["availability_requested"] is True
    assert result["validated_availability_signature"] is not None


def test_early_availability_continues_with_next_non_room_field(
    room: Room,
) -> None:
    adapter = Mock()
    adapter.execute.return_value = MatchResponse(
        None,  # type: ignore[arg-type]
        [room],
    )
    information = {
        InformationField.CHECK_IN: Information(
            InformationField.CHECK_IN,
            date(2030, 6, 10),
        ),
        InformationField.CHECK_OUT: Information(
            InformationField.CHECK_OUT,
            date(2030, 6, 13),
        ),
    }

    result = execute_domain_action(
        _context(adapter),
        _state(
            domain_operation=DomainOperation.CHECK_BOOKING_AVAILABILITY,
            next_missing_field=InformationField.FIRST_NAME,
            missing_fields=[InformationField.FIRST_NAME],
            collected_information=information,
        ),
    )

    assert result["action"] is Action.ASK_FOR_DATA
    assert result["domain_data"] == [InformationField.FIRST_NAME]


def test_early_availability_requires_requested_field(room: Room) -> None:
    adapter = Mock()
    adapter.execute.return_value = MatchResponse(
        None,  # type: ignore[arg-type]
        [room],
    )

    result = execute_domain_action(
        _context(adapter),
        _state(domain_operation=DomainOperation.CHECK_BOOKING_AVAILABILITY),
    )

    assert result["last_intent_fulfilled"] is False
    assert "response" in result
