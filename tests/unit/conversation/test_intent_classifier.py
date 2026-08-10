import pytest

from conversation.entities.message import Message
from conversation.information_extrator import DebugTestInput
from conversation.intent_classifier import IntentClassifier
from conversation.value_object.intent import Intent


@pytest.mark.parametrize(
    ("raw_message", "expected_intent"),
    [
        (DebugTestInput.AVAILABILIY_CHECK, Intent.AVAILABILITY_CHECK),
        (DebugTestInput.BOOKING_CHECK, Intent.BOOKING_CHECK),
        (DebugTestInput.BOOKING_CANCELLATION, Intent.BOOKING_CANCELLATION),
        (DebugTestInput.BOOKING_REQUEST, Intent.BOOKING_REQUEST),
        (DebugTestInput.INFORMATION_REQUEST, Intent.INFORMATION_REQUEST),
        (DebugTestInput.BULLSHIT, Intent.UNKNOWN),
        ("something else", Intent.UNKNOWN),
    ],
)
def test_determine_maps_debug_messages_to_intent(
    raw_message: str,
    expected_intent: Intent,
) -> None:
    message = Message(raw_message, original_content=raw_message)

    assert IntentClassifier().determine(message) is expected_intent
