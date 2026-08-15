"""Regression tests for terminal booking state and fresh room offers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

from conversation.entities.information import Information
from conversation.entities.interaction_response import BookingResponseObject
from conversation.entities.message import Message
from conversation.graph.nodes.activate_intent import activate_intent
from conversation.graph.nodes.classify_intent import classify_intent
from conversation.graph.nodes.context import ConversationNodeContext
from conversation.graph.nodes.determine_action import determine_action
from conversation.graph.nodes.determine_missing_fields import determine_missing_fields
from conversation.graph.nodes.execute_domain_action import execute_domain_action
from conversation.graph.nodes.extract_information import extract_information
from conversation.graph.nodes.resolve_confirmation import resolve_confirmation
from conversation.graph.nodes.support import _booking_availability_signature
from conversation.graph.nodes.update_progress import update_progress
from conversation.graph.reducers import merge_information
from conversation.graph.state import (
    ConversationState,
    DomainOperation,
    ExpectedInteraction,
    ExpectedInteractionKind,
)
from conversation.value_object.action import Action
from conversation.value_object.booking_selection import BookingSelection
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.services.find_matching_rooms import MatchResponse
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod

CHECK_IN = date(2030, 6, 10)
CHECK_OUT = date(2030, 6, 13)


def _state(**values: object) -> ConversationState:
    return cast(ConversationState, values)


def _context(*, domain_result: object | None = None) -> ConversationNodeContext:
    domain_adapter = Mock()
    domain_adapter.execute.return_value = domain_result
    return cast(
        ConversationNodeContext,
        SimpleNamespace(
            domain_adapter=domain_adapter,
            information_extractor=Mock(),
            max_unknown_messages=2,
        ),
    )


def _booking_information() -> dict[InformationField, Information]:
    return {
        InformationField.CHECK_IN: Information(
            InformationField.CHECK_IN,
            CHECK_IN,
        ),
        InformationField.CHECK_OUT: Information(
            InformationField.CHECK_OUT,
            CHECK_OUT,
        ),
        InformationField.GUEST_COUNT: Information(
            InformationField.GUEST_COUNT,
            2,
        ),
        InformationField.ACCESSIBLE: Information(
            InformationField.ACCESSIBLE,
            False,
        ),
        InformationField.BREAKFAST: Information(
            InformationField.BREAKFAST,
            True,
        ),
        InformationField.FIRST_NAME: Information(
            InformationField.FIRST_NAME,
            "Alex",
        ),
        InformationField.LAST_NAME: Information(
            InformationField.LAST_NAME,
            "Morgan",
        ),
        InformationField.EMAIL: Information(
            InformationField.EMAIL,
            "alex@example.com",
        ),
        InformationField.PHONE: Information(
            InformationField.PHONE,
            "+49 123 456789",
        ),
        InformationField.PREFERRED_LANG: Information(
            InformationField.PREFERRED_LANG,
            "de",
        ),
        InformationField.ROOM_CATEGORY: Information(
            InformationField.ROOM_CATEGORY,
            RoomCategory.DOUBLE,
        ),
    }


def _booking_response() -> BookingResponseObject:
    return BookingResponseObject(
        status=BookingStatus.CONFIRMED,
        room_category=RoomCategory.DOUBLE,
        guest_count=2,
        check_in=CHECK_IN,
        check_out=CHECK_OUT,
        total_prize=Money(Decimal("300.00"), "EUR"),
        accessible=False,
        breakfast=True,
        first_name="Alex",
        last_name="Morgan",
        email="alex@example.com",
        phone="+49 123 456789",
    )


def _effective_information(
    current: dict[InformationField, Information],
    updates: object,
) -> dict[InformationField, Information]:
    return merge_information(
        current,
        cast(dict[InformationField, Information | None], updates),
    )


def test_successful_booking_keeps_only_identity_phone_and_check_in() -> None:
    collected = _booking_information()
    state = _state(
        domain_operation=DomainOperation.CREATE_BOOKING,
        collected_information=collected,
        availability_requested=True,
        validated_availability_signature=(
            CHECK_IN.isoformat(),
            CHECK_OUT.isoformat(),
            2,
            False,
            RoomCategory.DOUBLE,
        ),
    )

    updates = execute_domain_action(
        _context(domain_result=_booking_response()),
        state,
    )
    effective = _effective_information(
        collected,
        updates["collected_information"],
    )

    assert set(effective) == {
        InformationField.CHECK_IN,
        InformationField.FIRST_NAME,
        InformationField.LAST_NAME,
        InformationField.EMAIL,
        InformationField.PHONE,
    }
    assert updates["availability_requested"] is False
    assert updates["validated_availability_signature"] is None
    assert updates["last_booking_check_in"] is collected[InformationField.CHECK_IN]
    assert updates["missing_fields"] == []
    assert updates["next_missing_field"] is None


def test_declined_booking_keeps_all_collected_information() -> None:
    collected = _booking_information()
    previous_check_in = Information(
        InformationField.CHECK_IN,
        date(2029, 12, 1),
    )
    expected = ExpectedInteraction(
        kind=ExpectedInteractionKind.BOOKING_CONFIRMATION,
        intent=Intent.BOOKING_REQUEST,
        operation=DomainOperation.CREATE_BOOKING,
    )
    state = _state(
        expected_interaction=expected,
        translated_message=Message("no"),
        extracted_information=[
            Information(InformationField.CONFIRMATION, "no")
        ],
        changed_fields=[],
        collected_information=collected,
        availability_requested=True,
        last_booking_check_in=previous_check_in,
        validated_availability_signature=(
            CHECK_IN.isoformat(),
            CHECK_OUT.isoformat(),
            2,
            False,
            RoomCategory.DOUBLE,
        ),
    )

    updates = resolve_confirmation(_context(), state)

    assert "collected_information" not in updates
    assert state["collected_information"] == collected
    assert updates["availability_requested"] is False
    assert updates["validated_availability_signature"] is None
    assert "last_booking_check_in" not in updates


def test_booking_preview_does_not_replace_confirmed_booking_reference() -> None:
    previous_check_in = Information(
        InformationField.CHECK_IN,
        date(2029, 12, 1),
    )

    updates = execute_domain_action(
        _context(domain_result=_booking_response()),
        _state(
            domain_operation=DomainOperation.PREVIEW_BOOKING,
            collected_information=_booking_information(),
            last_booking_check_in=previous_check_in,
        ),
    )

    assert "last_booking_check_in" not in updates
    assert updates["action"] is Action.ASK_FOR_CONFIRMATION


def test_new_availability_keeps_all_collected_information() -> None:
    last_booking_check_in = Information(InformationField.CHECK_IN, CHECK_IN)
    state = _state(
        current_intent=Intent.BOOKING_REQUEST,
        detected_intent=Intent.AVAILABILITY_CHECK,
        last_intent_fulfilled=True,
        extracted_information=[],
        changed_fields=[],
        collected_information={
            InformationField.CHECK_IN: last_booking_check_in,
            InformationField.ROOM_CATEGORY: Information(
                InformationField.ROOM_CATEGORY,
                RoomCategory.DOUBLE,
            ),
        },
        availability_requested=True,
        last_booking_check_in=last_booking_check_in,
    )

    updates = activate_intent(_context(), state)

    assert "collected_information" not in updates
    assert state["collected_information"][InformationField.CHECK_IN] is (
        last_booking_check_in
    )
    assert InformationField.ROOM_CATEGORY in state["collected_information"]
    assert updates["availability_requested"] is False
    assert state["last_booking_check_in"] is last_booking_check_in


def test_booking_lookup_restores_last_booking_check_in() -> None:
    last_booking_check_in = Information(InformationField.CHECK_IN, CHECK_IN)
    state = _state(
        current_intent=Intent.AVAILABILITY_CHECK,
        detected_intent=Intent.BOOKING_CANCELLATION,
        last_intent_fulfilled=False,
        extracted_information=[],
        changed_fields=[],
        collected_information={},
        last_booking_check_in=last_booking_check_in,
    )

    updates = activate_intent(_context(), state)

    assert updates["collected_information"] == {
        InformationField.CHECK_IN: last_booking_check_in
    }
    assert updates["current_intent"] is Intent.BOOKING_CANCELLATION


def test_restored_check_in_is_not_requested_again_for_booking_lookup() -> None:
    last_booking_check_in = Information(InformationField.CHECK_IN, CHECK_IN)
    collected = {
        InformationField.LAST_NAME: Information(
            InformationField.LAST_NAME,
            "Morgan",
        ),
        InformationField.EMAIL: Information(
            InformationField.EMAIL,
            "alex@example.com",
        ),
    }
    activation = activate_intent(
        _context(),
        _state(
            current_intent=Intent.AVAILABILITY_CHECK,
            detected_intent=Intent.BOOKING_CHECK,
            last_intent_fulfilled=False,
            extracted_information=[],
            changed_fields=[],
            collected_information=collected,
            last_booking_check_in=last_booking_check_in,
        ),
    )
    effective = _effective_information(
        collected,
        activation["collected_information"],
    )

    missing = determine_missing_fields(
        _context(),
        _state(
            current_intent=Intent.BOOKING_CHECK,
            collected_information=effective,
        ),
    )

    assert missing["missing_fields"] == []
    assert missing["next_missing_field"] is None


def test_explicit_lookup_date_takes_precedence_over_booking_reference() -> None:
    explicit_check_in = Information(
        InformationField.CHECK_IN,
        date(2031, 1, 5),
    )
    state = _state(
        current_intent=Intent.AVAILABILITY_CHECK,
        detected_intent=Intent.BOOKING_CHECK,
        last_intent_fulfilled=False,
        extracted_information=[explicit_check_in],
        changed_fields=[InformationField.CHECK_IN],
        last_booking_check_in=Information(InformationField.CHECK_IN, CHECK_IN),
    )

    updates = activate_intent(_context(), state)

    assert "collected_information" not in updates
    assert updates["current_intent"] is Intent.BOOKING_CHECK


def test_missing_room_category_runs_availability_even_for_validated_signature() -> None:
    collected = _booking_information()
    collected.pop(InformationField.ROOM_CATEGORY)
    signature = _booking_availability_signature(collected)

    updates = determine_action(
        _context(),
        _state(
            current_intent=Intent.BOOKING_REQUEST,
            missing_fields=[InformationField.ROOM_CATEGORY],
            next_missing_field=InformationField.ROOM_CATEGORY,
            collected_information=collected,
            validated_availability_signature=signature,
        ),
    )

    assert updates == {
        "domain_operation": DomainOperation.CHECK_BOOKING_AVAILABILITY,
        "next_missing_field": InformationField.ROOM_CATEGORY,
        "last_intent_fulfilled": False,
    }


def test_room_category_availability_check_displays_fresh_room_cards() -> None:
    collected = _booking_information()
    collected.pop(InformationField.ROOM_CATEGORY)
    request = BookingRequest(
        request_id="request-1",
        stay_period=StayPeriod(CHECK_IN, CHECK_OUT),
        guest_count=2,
        breakfast_included=True,
        accessible_requested=False,
    )
    room = Room(
        room_id="room-1",
        room_number="101",
        floor=1,
        category=RoomCategory.DOUBLE,
        max_occupancy=2,
        price_per_night=Money(Decimal("100.00"), "EUR"),
        is_accessible=True,
    )

    updates = execute_domain_action(
        _context(domain_result=MatchResponse(request=request, rooms=[room])),
        _state(
            domain_operation=DomainOperation.CHECK_BOOKING_AVAILABILITY,
            current_intent=Intent.BOOKING_REQUEST,
            next_missing_field=InformationField.ROOM_CATEGORY,
            collected_information=collected,
        ),
    )

    assert updates["action"] is Action.DISPLAY_AVAILABILITY
    assert updates["availability_requested"] is True
    assert updates["last_intent_fulfilled"] is False
    assert updates["domain_data"] == MatchResponse(request=request, rooms=[room])


def test_information_question_preserves_active_availability_fields() -> None:
    collected = {
        InformationField.CHECK_IN: Information(
            InformationField.CHECK_IN,
            CHECK_IN,
        ),
        InformationField.CHECK_OUT: Information(
            InformationField.CHECK_OUT,
            CHECK_OUT,
        ),
    }
    topic = Information(
        InformationField.INFORMATION_TOPIC,
        InformationTopic.ROOM_CATEGORIES,
    )
    progress_updates = update_progress(
        _context(),
        _state(
            current_intent=Intent.AVAILABILITY_CHECK,
            detected_intent=Intent.INFORMATION_REQUEST,
            last_intent_fulfilled=False,
            next_missing_field=InformationField.GUEST_COUNT,
            expected_interaction=None,
            parsed_message=Message("What room categories do you have?"),
            translated_message=Message("What room categories do you have?"),
            extracted_information=[topic],
            original_message_extracted_fields=[],
            collected_information=collected,
            pending_information_changes={},
            unknown_counter=0,
        ),
    )
    with_topic = _effective_information(
        collected,
        progress_updates["collected_information"],
    )

    assert with_topic == collected | {InformationField.INFORMATION_TOPIC: topic}

    information_updates = execute_domain_action(
        _context(domain_result="Several room categories are available."),
        _state(
            domain_operation=DomainOperation.GET_INFORMATION,
            collected_information=with_topic,
        ),
    )
    after_information = _effective_information(
        with_topic,
        information_updates["collected_information"],
    )

    assert after_information == collected


def test_pool_information_topic_is_accepted() -> None:
    topic = Information(
        InformationField.INFORMATION_TOPIC,
        InformationTopic.POOL,
    )
    message = Message("Does the hotel have a swimming pool?")

    updates = update_progress(
        _context(),
        _state(
            current_intent=Intent.INFORMATION_REQUEST,
            detected_intent=Intent.INFORMATION_REQUEST,
            last_intent_fulfilled=False,
            next_missing_field=None,
            expected_interaction=None,
            parsed_message=message,
            translated_message=message,
            extracted_information=[topic],
            original_message_extracted_fields=[],
            collected_information={},
            pending_information_changes={},
            unknown_counter=0,
        ),
    )

    assert updates["extracted_information"] == [topic]
    assert updates["collected_information"] == {
        InformationField.INFORMATION_TOPIC: topic
    }


def test_failed_booking_creation_keeps_collected_information() -> None:
    collected = _booking_information()
    collected_before = dict(collected)
    context = _context()
    context.domain_adapter.execute.side_effect = RuntimeError("backend failed")
    context.user_interaction = Mock()
    context.user_interaction.send_error_msg.return_value = None

    updates = execute_domain_action(
        context,
        _state(
            domain_operation=DomainOperation.CREATE_BOOKING,
            collected_information=collected,
            availability_requested=True,
            validated_availability_signature=(
                CHECK_IN.isoformat(),
                CHECK_OUT.isoformat(),
                2,
                False,
                RoomCategory.DOUBLE,
            ),
        ),
    )

    assert "collected_information" not in updates
    assert collected == collected_before
    assert updates["availability_requested"] is False
    assert updates["validated_availability_signature"] is None


def test_old_room_button_starts_fresh_availability_after_booking_reset() -> None:
    selection = BookingSelection(
        check_in=CHECK_IN,
        check_out=CHECK_OUT,
        guest_count=2,
        accessible=False,
        room_category=RoomCategory.DOUBLE,
    )

    updates = classify_intent(
        _context(),
        _state(
            translated_message=Message(selection.to_wire()),
            availability_requested=False,
        ),
    )

    assert updates["detected_intent"] is Intent.AVAILABILITY_CHECK


def test_booking_selection_keeps_both_dates_while_check_in_is_requested() -> None:
    selection = BookingSelection(
        check_in=CHECK_IN,
        check_out=CHECK_OUT,
        guest_count=2,
        accessible=False,
        room_category=RoomCategory.DOUBLE,
    )
    message = Message(selection.to_wire())
    state = _state(
        parsed_message=message,
        translated_message=message,
        current_intent=Intent.BOOKING_REQUEST,
        detected_intent=Intent.BOOKING_REQUEST,
        last_intent_fulfilled=False,
        next_missing_field=InformationField.CHECK_IN,
        missing_fields=[InformationField.CHECK_IN],
        expected_interaction=None,
        collected_information={},
        pending_information_changes={},
        unknown_counter=0,
    )

    extraction_updates = extract_information(_context(), state)
    progress_updates = update_progress(
        _context(),
        _state(**state, **extraction_updates),
    )

    assert {
        information.information_field
        for information in progress_updates["extracted_information"]
    } >= {
        InformationField.CHECK_IN,
        InformationField.CHECK_OUT,
    }
    assert set(progress_updates["collected_information"]) >= {
        InformationField.CHECK_IN,
        InformationField.CHECK_OUT,
    }
