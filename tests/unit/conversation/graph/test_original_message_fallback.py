"""Regression tests for requested-field extraction from original messages."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest

from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.graph.nodes.activate_intent import activate_intent
from conversation.graph.nodes.context import ConversationNodeContext
from conversation.graph.nodes.extract_information import extract_information
from conversation.graph.nodes.update_progress import update_progress
from conversation.graph.state import (
    ConversationState,
    DomainOperation,
    ExpectedInteraction,
    ExpectedInteractionKind,
)
from conversation.models.information.interface import InformationExtractorInterface
from conversation.value_object.action import Action
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


def _context(extractor: Mock) -> ConversationNodeContext:
    return cast(
        ConversationNodeContext,
        SimpleNamespace(
            information_extractor=extractor,
            max_unknown_messages=2,
        ),
    )


def _state(**values: object) -> ConversationState:
    return cast(ConversationState, values)


def _extractor() -> Mock:
    return Mock(spec=InformationExtractorInterface)


def test_missing_requested_fields_are_extracted_from_original_message() -> None:
    extractor = _extractor()
    original = Message("Ich heisse Max Mustermann.")
    translated = Message("I want to cancel.", original_content=original.content)
    first_name = Information(InformationField.FIRST_NAME, "Max")
    last_name = Information(InformationField.LAST_NAME, "Mustermann")
    extractor.extract.side_effect = [
        [],
        [
            first_name,
            last_name,
            Information(InformationField.GUEST_COUNT, 4),
        ],
    ]

    result = extract_information(
        _context(extractor),
        _state(
            parsed_message=original,
            translated_message=translated,
            current_intent=Intent.BOOKING_REQUEST,
            last_intent_fulfilled=False,
            next_missing_field=InformationField.FIRST_NAME,
            missing_fields=[
                InformationField.FIRST_NAME,
                InformationField.LAST_NAME,
            ],
            expected_interaction=None,
        ),
    )

    assert result["extracted_information"] == [first_name, last_name]
    assert result["original_message_extracted_fields"] == [
        InformationField.FIRST_NAME,
        InformationField.LAST_NAME,
    ]
    assert [
        call.kwargs["message"] for call in extractor.extract.call_args_list
    ] == [translated, original]


def test_primary_requested_field_does_not_trigger_second_extraction() -> None:
    extractor = _extractor()
    original = Message("Wir sind zu viert.")
    translated = Message("There are four of us.", original_content=original.content)
    guest_count = Information(InformationField.GUEST_COUNT, 4)
    extractor.extract.return_value = [guest_count]

    result = extract_information(
        _context(extractor),
        _state(
            parsed_message=original,
            translated_message=translated,
            current_intent=Intent.AVAILABILITY_CHECK,
            last_intent_fulfilled=False,
            next_missing_field=InformationField.GUEST_COUNT,
            missing_fields=[InformationField.GUEST_COUNT],
            expected_interaction=None,
        ),
    )

    assert result["extracted_information"] == [guest_count]
    extractor.extract.assert_called_once_with(message=translated)


def test_bare_integer_fills_requested_integer_field_when_extraction_is_empty() -> None:
    extractor = _extractor()
    original = Message(" 2 ")
    translated = Message("unrelated", original_content=original.content)
    extractor.extract.return_value = []

    result = extract_information(
        _context(extractor),
        _state(
            parsed_message=original,
            translated_message=translated,
            current_intent=Intent.AVAILABILITY_CHECK,
            last_intent_fulfilled=False,
            next_missing_field=InformationField.GUEST_COUNT,
            missing_fields=[InformationField.GUEST_COUNT],
            expected_interaction=None,
        ),
    )

    extracted = result["extracted_information"]
    assert len(extracted) == 1
    assert extracted[0].information_field is InformationField.GUEST_COUNT
    assert extracted[0].content == 2
    assert result["original_message_extracted_fields"] == [
        InformationField.GUEST_COUNT
    ]
    extractor.extract.assert_called_once_with(message=translated)


def test_bare_integer_is_authoritative_for_requested_integer_field() -> None:
    extractor = _extractor()
    original = Message("2")
    translated = Message("2", original_content=original.content)
    extracted_guest_count = Information(InformationField.GUEST_COUNT, 4)
    extractor.extract.return_value = [extracted_guest_count]

    result = extract_information(
        _context(extractor),
        _state(
            parsed_message=original,
            translated_message=translated,
            current_intent=Intent.AVAILABILITY_CHECK,
            last_intent_fulfilled=False,
            next_missing_field=InformationField.GUEST_COUNT,
            missing_fields=[InformationField.GUEST_COUNT],
            expected_interaction=None,
        ),
    )

    extracted = result["extracted_information"]
    assert len(extracted) == 1
    assert extracted[0].information_field is InformationField.GUEST_COUNT
    assert extracted[0].content == 2
    extractor.extract.assert_called_once_with(message=translated)


def test_original_literal_email_overrides_translator_hallucination() -> None:
    extractor = _extractor()
    original = Message("Meine E-Mail ist Real.User@example.de.")
    translated = Message(
        "My email is made.up@example.com.",
        original_content=original.content,
    )
    extractor.extract.return_value = [
        Information(InformationField.EMAIL, "made.up@example.com")
    ]

    result = extract_information(
        _context(extractor),
        _state(
            parsed_message=original,
            translated_message=translated,
            current_intent=Intent.BOOKING_REQUEST,
            last_intent_fulfilled=False,
            next_missing_field=InformationField.EMAIL,
            missing_fields=[InformationField.EMAIL],
            expected_interaction=None,
        ),
    )

    extracted = result["extracted_information"]
    assert len(extracted) == 1
    assert extracted[0].information_field is InformationField.EMAIL
    assert extracted[0].content == "Real.User@example.de"
    extractor.extract.assert_called_once_with(message=translated)


def test_nonliteral_email_hallucinations_are_not_accepted() -> None:
    extractor = _extractor()
    original = Message("Das habe ich nicht verstanden.")
    translated = Message(
        "My email is made.up@example.com.",
        original_content=original.content,
    )
    hallucinated_email = Information(
        InformationField.EMAIL,
        "made.up@example.com",
    )
    extractor.extract.side_effect = [
        [hallucinated_email],
        [hallucinated_email],
    ]

    result = extract_information(
        _context(extractor),
        _state(
            parsed_message=original,
            translated_message=translated,
            current_intent=Intent.BOOKING_REQUEST,
            last_intent_fulfilled=False,
            next_missing_field=InformationField.EMAIL,
            missing_fields=[InformationField.EMAIL],
            expected_interaction=None,
        ),
    )

    assert result["extracted_information"] == []
    assert extractor.extract.call_count == 2


def test_original_fallback_failure_preserves_primary_result() -> None:
    extractor = _extractor()
    original = Message("zwei Personen")
    translated = Message("unrelated", original_content=original.content)
    extractor.extract.side_effect = [[], RuntimeError("model failed")]

    result = extract_information(
        _context(extractor),
        _state(
            parsed_message=original,
            translated_message=translated,
            current_intent=Intent.AVAILABILITY_CHECK,
            last_intent_fulfilled=False,
            next_missing_field=InformationField.GUEST_COUNT,
            missing_fields=[InformationField.GUEST_COUNT],
            expected_interaction=None,
        ),
    )

    assert result["extracted_information"] == []
    assert extractor.extract.call_count == 2


def test_pending_confirmation_uses_original_without_second_extraction() -> None:
    extractor = _extractor()
    original = Message("ja")
    translated = Message("yes", original_content=original.content)
    extractor.extract.return_value = []
    expected = ExpectedInteraction(
        kind=ExpectedInteractionKind.BOOKING_CONFIRMATION,
        intent=Intent.BOOKING_REQUEST,
        operation=DomainOperation.CREATE_BOOKING,
    )

    result = extract_information(
        _context(extractor),
        _state(
            parsed_message=original,
            translated_message=translated,
            current_intent=Intent.BOOKING_REQUEST,
            last_intent_fulfilled=False,
            next_missing_field=InformationField.GUEST_COUNT,
            expected_interaction=expected,
        ),
    )

    assert result["extracted_information"] == []
    extractor.extract.assert_called_once_with(message=original)


def test_grouped_requested_field_keeps_current_intent() -> None:
    extractor = _extractor()
    email = Information(InformationField.EMAIL, "guest@example.de")
    state = _state(
        current_intent=Intent.BOOKING_REQUEST,
        detected_intent=Intent.BOOKING_CANCELLATION,
        last_intent_fulfilled=False,
        next_missing_field=InformationField.FIRST_NAME,
        missing_fields=[
            InformationField.FIRST_NAME,
            InformationField.LAST_NAME,
            InformationField.EMAIL,
        ],
        expected_interaction=None,
        extracted_information=[email],
        changed_fields=[InformationField.EMAIL],
    )

    assert activate_intent(_context(extractor), state) == {
        "current_intent": Intent.BOOKING_REQUEST,
        "last_intent_fulfilled": False,
    }


def test_recovered_requested_date_keeps_current_intent() -> None:
    extractor = _extractor()
    original = Message("Samstag")
    translated = Message("Saturday", original_content=original.content)
    check_in = datetime.now(UTC).astimezone().date() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    extractor.extract.side_effect = [
        [],
        [Information(InformationField.CHECK_IN, check_out)],
    ]
    state = _state(
        parsed_message=original,
        translated_message=translated,
        current_intent=Intent.AVAILABILITY_CHECK,
        detected_intent=Intent.BOOKING_CANCELLATION,
        last_intent_fulfilled=False,
        next_missing_field=InformationField.CHECK_OUT,
        missing_fields=[InformationField.CHECK_OUT],
        expected_interaction=None,
        collected_information={
            InformationField.CHECK_IN: Information(
                InformationField.CHECK_IN,
                check_in,
            )
        },
        unknown_counter=0,
    )

    extraction_update = extract_information(_context(extractor), state)
    progress_update = update_progress(
        _context(extractor),
        cast(ConversationState, {**state, **extraction_update}),
    )

    extracted = progress_update["extracted_information"]
    assert len(extracted) == 1
    assert extracted[0].information_field is InformationField.CHECK_OUT
    assert extracted[0].content == check_out
    assert progress_update["collected_information"] == {
        InformationField.CHECK_OUT: extracted[0]
    }

    intent_update = activate_intent(
        _context(extractor),
        cast(ConversationState, {**state, **progress_update}),
    )
    assert intent_update == {
        "current_intent": Intent.AVAILABILITY_CHECK,
        "last_intent_fulfilled": False,
    }


def test_recovered_date_is_validated_against_original_message() -> None:
    extractor = _extractor()
    check_in = datetime.now(UTC).astimezone().date() + timedelta(days=14)
    original = Message(check_in.strftime("%d.%m.%Y"))
    translated = Message(
        "The Commission shall adopt implementing acts.",
        original_content=original.content,
    )
    recovered = Information(InformationField.CHECK_IN, check_in)
    extractor.extract.side_effect = [[], [recovered]]
    state = _state(
        parsed_message=original,
        translated_message=translated,
        current_intent=Intent.AVAILABILITY_CHECK,
        detected_intent=Intent.UNKNOWN,
        last_intent_fulfilled=False,
        next_missing_field=InformationField.CHECK_IN,
        missing_fields=[InformationField.CHECK_IN],
        expected_interaction=None,
        collected_information={},
        unknown_counter=1,
    )

    extraction_update = extract_information(_context(extractor), state)
    progress_update = update_progress(
        _context(extractor),
        cast(ConversationState, {**state, **extraction_update}),
    )

    assert extraction_update["original_message_extracted_fields"] == [
        InformationField.CHECK_IN
    ]
    assert progress_update["extracted_information"] == [recovered]
    assert progress_update["collected_information"] == {
        InformationField.CHECK_IN: recovered
    }
    assert progress_update["unknown_counter"] == 0


def test_implausible_recovered_date_is_reported_for_requested_field() -> None:
    extractor = _extractor()
    original = Message("gestern")
    translated = Message("yesterday", original_content=original.content)
    today = datetime.now(UTC).astimezone().date()
    extractor.extract.side_effect = [
        [],
        [Information(InformationField.CHECK_IN, today - timedelta(days=1))],
    ]
    state = _state(
        parsed_message=original,
        translated_message=translated,
        current_intent=Intent.AVAILABILITY_CHECK,
        detected_intent=Intent.BOOKING_CANCELLATION,
        last_intent_fulfilled=False,
        next_missing_field=InformationField.CHECK_OUT,
        missing_fields=[InformationField.CHECK_OUT],
        expected_interaction=None,
        collected_information={
            InformationField.CHECK_IN: Information(
                InformationField.CHECK_IN,
                today + timedelta(days=1),
            )
        },
        unknown_counter=0,
    )

    extraction_update = extract_information(_context(extractor), state)
    progress_update = update_progress(
        _context(extractor),
        cast(ConversationState, {**state, **extraction_update}),
    )

    assert progress_update["action"] is Action.REPORT_INVALID_DATE
    assert progress_update["domain_data"] is InformationField.CHECK_OUT
    assert progress_update["current_intent"] is Intent.AVAILABILITY_CHECK
    assert progress_update["extracted_information"] == []


def test_ambiguous_single_date_can_replace_valid_check_out() -> None:
    check_in = datetime.now(UTC).astimezone().date() + timedelta(days=10)
    old_check_out = check_in + timedelta(days=10)
    new_check_out = check_in + timedelta(days=7)
    message = Message(new_check_out.strftime("%d.%m.%Y"))
    state = _state(
        parsed_message=message,
        translated_message=message,
        current_intent=Intent.BOOKING_REQUEST,
        detected_intent=Intent.UNKNOWN,
        last_intent_fulfilled=False,
        next_missing_field=InformationField.FIRST_NAME,
        expected_interaction=None,
        extracted_information=[
            Information(InformationField.CHECK_IN, new_check_out),
            Information(InformationField.CHECK_OUT, new_check_out),
        ],
        original_message_extracted_fields=[],
        collected_information={
            InformationField.CHECK_IN: Information(
                InformationField.CHECK_IN,
                check_in,
            ),
            InformationField.CHECK_OUT: Information(
                InformationField.CHECK_OUT,
                old_check_out,
            ),
        },
        pending_information_changes={},
        unknown_counter=0,
    )

    progress_update = update_progress(_context(_extractor()), state)

    pending = progress_update["pending_information_changes"]
    assert set(pending) == {InformationField.CHECK_OUT}
    assert pending[InformationField.CHECK_OUT].content == new_check_out
    assert progress_update["action"] is Action.ASK_FOR_INFORMATION_CHANGE


@pytest.mark.parametrize(
    "existing_field",
    [InformationField.CHECK_IN, InformationField.CHECK_OUT],
)
def test_repeated_stay_date_reports_existing_role(
    existing_field: InformationField,
) -> None:
    check_in = datetime.now(UTC).astimezone().date() + timedelta(days=10)
    check_out = check_in + timedelta(days=5)
    repeated_date = check_in if existing_field is InformationField.CHECK_IN else check_out
    message = Message(repeated_date.strftime("%d.%m.%Y"))
    state = _state(
        parsed_message=message,
        translated_message=message,
        current_intent=Intent.BOOKING_REQUEST,
        detected_intent=Intent.UNKNOWN,
        last_intent_fulfilled=False,
        next_missing_field=InformationField.FIRST_NAME,
        expected_interaction=None,
        extracted_information=[
            Information(InformationField.CHECK_IN, repeated_date),
            Information(InformationField.CHECK_OUT, repeated_date),
        ],
        original_message_extracted_fields=[],
        collected_information={
            InformationField.CHECK_IN: Information(
                InformationField.CHECK_IN,
                check_in,
            ),
            InformationField.CHECK_OUT: Information(
                InformationField.CHECK_OUT,
                check_out,
            ),
        },
        pending_information_changes={},
        unknown_counter=0,
    )

    progress_update = update_progress(_context(_extractor()), state)

    assert progress_update["action"] is Action.REPORT_REUSED_DATE
    assert progress_update["domain_data"] is existing_field
    assert progress_update["collected_information"] == {}
