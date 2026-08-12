from enum import StrEnum


class Action(StrEnum):
    ASK_FOR_DATA="ask_for_data"
    ASK_FOR_CONFIRMATION="ask_for_confirmation"
    ASK_FOR_INFORMATION_CHANGE="ask_for_information_change"
    REPORT_INVALID_DATE="report_invalid_date"
    DISPLAY_INFO="display_info"
    DISPLAY_AVAILABILITY="display_availability"
    DISPLAY_BOOKING="display_booking"
    DISPLAY_GREETING="display_greeting"
    ASK_INTENT="ask_intent"
    CONFIRMATION_DECLINED="confirmation_declined"

