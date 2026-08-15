"""Focused tests for deterministic intent-classification routing."""

from datetime import date
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

from conversation.entities.message import Message
from conversation.graph.nodes.classify_intent import classify_intent
from conversation.graph.nodes.context import ConversationNodeContext
from conversation.graph.state import ConversationState
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.value_object.booking_selection import BookingSelection
from conversation.value_object.intent import Intent
from domain.value_objects.room_category import RoomCategory


def _context(classifier: Mock) -> ConversationNodeContext:
    return cast(
        ConversationNodeContext,
        SimpleNamespace(intent_classifier=classifier),
    )


def _state(**values: object) -> ConversationState:
    return cast(ConversationState, values)


def test_booking_selection_bypasses_model_classifier() -> None:
    classifier = Mock(spec=IntentionDetectorInterface)
    wire = BookingSelection(
        check_in=date(2030, 6, 10),
        check_out=date(2030, 6, 13),
        guest_count=2,
        accessible=False,
        room_category=RoomCategory.DOUBLE,
    ).to_wire()

    result = classify_intent(
        _context(classifier),
        _state(translated_message=Message(wire), availability_requested=True),
    )

    assert result == {"detected_intent": Intent.BOOKING_REQUEST}
    classifier.determine.assert_not_called()


def test_booking_request_starts_with_availability_when_not_requested() -> None:
    classifier = Mock(spec=IntentionDetectorInterface)
    classifier.determine.return_value = Intent.BOOKING_REQUEST

    result = classify_intent(
        _context(classifier),
        _state(
            translated_message=Message("Book a room"),
            availability_requested=False,
        ),
    )

    assert result == {"detected_intent": Intent.AVAILABILITY_CHECK}


def test_classifier_exception_falls_back_to_unknown() -> None:
    classifier = Mock(spec=IntentionDetectorInterface)
    classifier.determine.side_effect = RuntimeError("model failed")

    result = classify_intent(
        _context(classifier),
        _state(translated_message=Message("Hello")),
    )

    assert result == {"detected_intent": Intent.UNKNOWN}


def test_invalid_classifier_value_falls_back_to_unknown() -> None:
    classifier = Mock(spec=IntentionDetectorInterface)
    classifier.determine.return_value = "not-an-intent"

    result = classify_intent(
        _context(classifier),
        _state(translated_message=Message("Hello")),
    )

    assert result == {"detected_intent": Intent.UNKNOWN}
