from enum import StrEnum


class DefaultPhrases(StrEnum):
    GREETING = "Welcome! How can I help you?"
    CONFIRM_BOOKING = "Please check booking Details and click on confirm"
    CANCEL_BOOKING = "Are you sure, you want to cancel this booking?"
    UNKNOWN_INTENT = "Unfortunately, I was not able to understand you. Please try again."
    ERROR_MESSAGE = "Something went terribly wrong!"

