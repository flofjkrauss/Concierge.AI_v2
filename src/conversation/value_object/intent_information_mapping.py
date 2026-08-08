"""dataclass to map required information fields to intents"""
from dataclasses import dataclass

from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


@dataclass(slots=True, frozen=True)
class IntentInformationMapper:
    """maps InformationField fields to corresponding intents"""
    @classmethod
    def determine_fields(self, intent: Intent) -> list[InformationField]:
        retval = []
        match intent:
            case Intent.AVAILABILITY_CHECK:
                retval.append(InformationField.CHECK_IN)
                retval.append(InformationField.CHECK_OUT)
                retval.append(InformationField.GUEST_COUNT)
                retval.append(InformationField.ACCESSIBLE)
            case Intent.BOOKING_CHECK:
                retval.append(InformationField.LAST_NAME)
                retval.append(InformationField.EMAIL)
                retval.append(InformationField.CHECK_IN)
            case Intent.BOOKING_CANCELLATION:
                retval.append(InformationField.LAST_NAME)
                retval.append(InformationField.EMAIL)
                retval.append(InformationField.CHECK_IN)
            case Intent.BOOKING_REQUEST:
                retval.append(InformationField.CHECK_IN)
                retval.append(InformationField.CHECK_OUT)
                retval.append(InformationField.GUEST_COUNT)
                retval.append(InformationField.ACCESSIBLE)
                retval.append(InformationField.BREAKFAST)
                retval.append(InformationField.FIRST_NAME)
                retval.append(InformationField.LAST_NAME)
                retval.append(InformationField.EMAIL)
            case Intent.INFORMATION_REQUEST:
                retval.append(InformationField.INFORMATION_TOPIC)
            case Intent.CONVERSATION_INITIATION:
                pass
            case Intent.UNKNOWN:
                pass

        return retval
