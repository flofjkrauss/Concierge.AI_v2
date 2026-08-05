from enum import StrEnum


class Intent(StrEnum):
    AVAILABILITY_CHECK = "availability_check"
    BOOKING_CHECK = "booking_check"
    BOOKING_REQUEST = "booking_request"
    BOOKING_CANCELLATION = "booking_cancellation"
    INFORMATION_REQUEST = "information_request"
    CONVERSATION_INITIATION = "conversation_initiation"
    UNKNOWN = "unknown"