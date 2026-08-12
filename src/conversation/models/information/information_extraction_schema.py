"""Schema and field map for information extraction"""

from conversation.value_object.information_fields import InformationField
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.room_category import RoomCategory


def get_information_extraction_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "check_in": {
                "type": "string",
                "format": "date",
            },
            "check_out": {
                "type": "string",
                "format": "date",
            },
            "guest_count": {"type": "integer"},
            "breakfast": {"type": "boolean"},
            "accessible": {"type": "boolean"},
            "information_topic": {
                "type": "string",
                "enum": [topic.value for topic in InformationTopic],
            },
            "room_category": {
                "type": "string",
                "enum": [category.value for category in RoomCategory],
            },
            "confirmation": {
                "type": "string",
                "enum": ["yes", "no"],
            },
        },
        "additionalProperties": False,
    }


def get_field_map() -> dict[str, InformationField]:
    return {
        "first_name": InformationField.FIRST_NAME,
        "last_name": InformationField.LAST_NAME,
        "email": InformationField.EMAIL,
        "phone": InformationField.PHONE,
        "check_in": InformationField.CHECK_IN,
        "check_out": InformationField.CHECK_OUT,
        "guest_count": InformationField.GUEST_COUNT,
        "breakfast": InformationField.BREAKFAST,
        "accessible": InformationField.ACCESSIBLE,
        "preferred_language": InformationField.PREFERRED_LANG,
        "booking_id": InformationField.BOOKING_ID,
        "information_topic": InformationField.INFORMATION_TOPIC,
        "room_category": InformationField.ROOM_CATEGORY,
        "confirmation": InformationField.CONFIRMATION,
    }
