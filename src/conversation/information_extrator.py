"""extract informations from user messages"""
from datetime import date

from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.value_object.information_fields import InformationField
from domain.value_objects.information_topic import InformationTopic

#debugging helper class
class DebugTestInput:
    AVAILABILIY_CHECK = "show availability"
    BOOKING_CHECK = "show booking"
    BOOKING_CANCELLATION = "cancel booking"
    BOOKING_REQUEST = "request booking"
    INFORMATION_REQUEST = "request info"
    BULLSHIT = "fuckyou"

class InformationExtractor:

    def extract(self, message: Message) -> list[Information]:
        """try to extract information fields from given user message"""

        # TODO: apply module for intent extraction here
        # do some dark magic again
        if message.original_content == "yes" or message.original_content == "no":
            return []

        # the following is just for testing and has to be remained later
        first_name = Information(
            information_field=InformationField.FIRST_NAME,
            content="Venom"
        )
        email = Information(
                    information_field=InformationField.EMAIL,
                    content="mail@mail.com"
                )
        check_in = Information(
                    information_field=InformationField.CHECK_IN,
                    content=date(2027, 8, 8)
                )
        check_out = Information(
                            information_field=InformationField.CHECK_OUT,
                            content=date(2027, 8, 11)
                        )

        guest_count = Information(
             information_field=InformationField.GUEST_COUNT,
             content=2
        )
        breakfast = Information(
                     information_field=InformationField.BREAKFAST,
                     content=True
                )
        accessible = Information(
                     information_field=InformationField.ACCESSIBLE,
                     content=False
                )
        booking_id = Information(
                     information_field=InformationField.BOOKING_ID,
                     content="none"
                )
        information_topic = Information(
                     information_field=InformationField.INFORMATION_TOPIC,
                     content=InformationTopic.WIFI
                )
        preferred_language = Information(
                     information_field=InformationField.PREFERRED_LANG,
                     content="et"
                )
        phone = Information(
                     information_field=InformationField.PHONE,
                     content="i got no phone"
                )
        last_name = Information(
                     information_field=InformationField.LAST_NAME,
                     content="user"
                )
        information_topic = Information(
            information_field=InformationField.INFORMATION_TOPIC,
            content=InformationTopic.AIRPORT_TRANSFER
        )
        print("extractor: ", message.content)
        match message.original_content:
            case DebugTestInput.AVAILABILIY_CHECK:
                return [guest_count, check_out, accessible, check_in]
            case DebugTestInput.BOOKING_CANCELLATION:
                return [last_name, check_in, email]
            case DebugTestInput.BOOKING_CHECK:
                return [last_name,check_in, email]
            case DebugTestInput.BOOKING_REQUEST:
                return [first_name, last_name, guest_count, check_out, accessible, check_in, breakfast, email]
            case DebugTestInput.INFORMATION_REQUEST:
                return [information_topic]
            case DebugTestInput.BULLSHIT:
                return []
        
        return []