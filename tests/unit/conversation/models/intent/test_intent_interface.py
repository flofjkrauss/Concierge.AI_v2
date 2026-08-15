"""Tests for intent-detector interfaces and deterministic doubles."""

import pytest

from conversation.entities.message import Message
from conversation.models.information.interface import DebugTestInput
from conversation.models.intent.interface import (
    DummyIntentClassifier,
    IntentionDetectorInterface,
)
from conversation.value_object.intent import Intent


def test_intention_detector_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        IntentionDetectorInterface()


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (DebugTestInput.AVAILABILIY_CHECK, Intent.AVAILABILITY_CHECK),
        (DebugTestInput.BOOKING_REQUEST, Intent.BOOKING_REQUEST),
        (DebugTestInput.INFORMATION_REQUEST, Intent.INFORMATION_REQUEST),
        ("unknown", Intent.UNKNOWN),
    ],
)
def test_dummy_classifier_maps_debug_messages(
    message: str,
    expected: Intent,
) -> None:
    result = DummyIntentClassifier().determine(
        Message(message, original_content=message)
    )

    assert result is expected
