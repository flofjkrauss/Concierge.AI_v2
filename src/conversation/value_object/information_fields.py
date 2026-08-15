from enum import StrEnum


class InformationField(StrEnum):
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    GUEST_COUNT = "guest_count"
    BREAKFAST = "breakfast_included"
    ACCESSIBLE = "accessible_requested"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    EMAIL = "email"
    BOOKING_ID = "booking_id"
    INFORMATION_TOPIC = "information_topic"
    PREFERRED_LANG = "preferred_language"
    PHONE = "phone"
    ROOM_CATEGORY = "room_category"
    CONFIRMATION = "confirmation"


