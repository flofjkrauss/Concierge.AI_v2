"""extract informations from user messages"""
from datetime import date
from abc import ABC, abstractmethod

from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.value_object.information_fields import InformationField
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.room_category import RoomCategory


#debugging helper class
class DebugTestInput:
    AVAILABILIY_CHECK = "show availability"
    BOOKING_CHECK = "show booking"
    BOOKING_CANCELLATION = "cancel booking"
    BOOKING_REQUEST = "request booking"
    INFORMATION_REQUEST = "request info"
    BULLSHIT = "bla"

class InformationExtractorInterface(ABC):
    """Define the data operations required by the business services."""

    @abstractmethod
    def extract(self, message: Message) -> list[Information]:
        """extract information fields from given user message"""
        

class DummyInformationExtractor:

    def extract(self, message: Message) -> list[Information]:
        """Return manually set information fields depending on message.original_content keywords"""

        if message.original_content == "yes" or message.original_content == "no":
            return []

        # the following is just for testing and has to be remained later
        first_name = Information(
            information_field=InformationField.FIRST_NAME,
            content="Venom"
        )
        email = Information(
                    information_field=InformationField.EMAIL,
                    content="venom@world-dominion.com"
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

        room_category = Information(
            information_field=InformationField.ROOM_CATEGORY,
            content=RoomCategory.FAMILY
        )
        return [first_name, last_name, guest_count, check_out, accessible, check_in, breakfast, email, preferred_language, room_category, phone, information_topic]
       #print("extractor: ", message.original_content)
        match message.original_content:
            case DebugTestInput.AVAILABILIY_CHECK:
                return [guest_count, check_out, accessible, check_in]
            case DebugTestInput.BOOKING_CANCELLATION:
                return [last_name, check_in, email]
            case DebugTestInput.BOOKING_CHECK:
                return [last_name,check_in, email]
            case DebugTestInput.BOOKING_REQUEST:
                return [first_name, last_name, guest_count, check_out, accessible, check_in, breakfast, email, preferred_language, room_category, phone]
            case DebugTestInput.INFORMATION_REQUEST:
                return [information_topic]
            case DebugTestInput.BULLSHIT:
                return []
        
        return []