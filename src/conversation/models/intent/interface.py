"""Generic interface for intention detection modules."""

from abc import ABC, abstractmethod

from conversation.entities.message import Message
from conversation.value_object.intent import Intent


#debug
from conversation.information_extrator import DebugTestInput



class IntentionDetectorInterface(ABC):
    """Define the data operations required by the business services."""

    @abstractmethod
    def determine(self, text: Message) -> Intent:
        """Tries to determine the language of text"""


class DummyIntentClassifier(IntentionDetectorInterface):
    def determine(self, message: Message) -> Intent:
        """try to determine which user intent is behind the given message"""

        match message.original_content:
            case DebugTestInput.AVAILABILIY_CHECK:
                return Intent.AVAILABILITY_CHECK
            case DebugTestInput.BOOKING_CANCELLATION:
                return Intent.BOOKING_CANCELLATION
            case DebugTestInput.BOOKING_CHECK:
                return Intent.BOOKING_CHECK
            case DebugTestInput.BOOKING_REQUEST:
                return Intent.BOOKING_REQUEST
            case DebugTestInput.INFORMATION_REQUEST:
                return Intent.INFORMATION_REQUEST
            case DebugTestInput.BULLSHIT:
                return Intent.UNKNOWN
            
        return Intent.UNKNOWN