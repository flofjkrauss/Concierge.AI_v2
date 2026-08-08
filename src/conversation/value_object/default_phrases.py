from __future__ import annotations
from enum import StrEnum


from conversation.value_object.information_fields import InformationField
from conversation.value_object.action import Action
from conversation.value_object.intent import Intent

from observability.log_messages import LOG_MSG

class DefaultPhrases(StrEnum):
    GREETING = "Welcome! How can I help you?"
    ASK_INTENT = "Unfortunately, I was not able to understand you. Please try again."
    ERROR_MESSAGE = "Something went terribly wrong!"
    AVAILABLE_ROOM_CATEGORIES = "According to your request, these room categories are available...."
    NO_VACANCY = "Unfortunately, we have no vacancy in the requested stay period."
    AVAILABILITY_ASK_FOR_DATA = "To offer possible booking options, I need to collect additional data. Please tell me:"
    ASK_CHECK_IN = "When would you like to check in?"
    ASK_CHECK_OUT = "When yould you like to check out?"
    ASK_CHECK_IN_AND_CHECK_OUT = "During what timeframe may we welcome you?"
    ASK_ACCESABILITY = "Do you need an accessible room?"
    ASK_NUMBER_GUESTS = "How many people are you?"
    BOOKING_ASK_FOR_DATA = "To complete your booking, I still need some information."
    CANCELLATION_ASK_FOR_DATA = "To complete your cancellation, I still need some information."
    ASK_FIRST_AND_LAST_NAME = "Please tell me your full name."
    ASK_FIRST_NAME = "Please tell me your first name."
    ASK_LAST_NAME = "Please tell me your family name."
    ASK_EMAIL = "Please tell me your email address."
    ASK_BREAKFAST = "Would you like to book breakfast aswell?"
    ASK_CONFIRMATION_CANCELLATION = "Are you sure you want to cancel this booking?"
    ASK_CONFIRMATION_BOOKING = "Please check the data and confirm your booking request."
    BOOKING_CHECK_ASK_FOR_DATA = "To find your booking I need additional information."
    DISPLAY_BOOKING = "Your booking:"
    BOOKING_NOT_FOUND = "I could not find any booking that matches the provided informations."
    REPEAT_ASK_CONFIRMATION = "I am sorry, I was not able to understand you. Did you confirm the last request?"
    NEED_ANYTHNG_ELSE = "Your request has been processed. Anything else I can help you out with?"




def build(action: Action, intent: Intent, missing_fields: list[InformationField]) -> str:
    match action:
        case Action.ASK_FOR_DATA:
            return build_ask_data(intent=intent, missing_fields=missing_fields)
        case Action.ASK_FOR_CONFIRMATION:
            return build_ask_confirmation(intent=intent, missing_fields=missing_fields)


def build_ask_confirmation(intent: Intent, missing_fields: list[InformationField]) -> str:
    if missing_fields:
        LOG_MSG.debug("Missing fields in confirmation branch", extra=missing_fields)
        return DefaultPhrases.REPEAT_ASK_CONFIRMATION
    match intent:
        case Intent.BOOKING_CANCELLATION:
            return DefaultPhrases.ASK_CONFIRMATION_CANCELLATION
        case Intent.BOOKING_REQUEST:
            return DefaultPhrases.ASK_CONFIRMATION_BOOKING

def build_ask_data(intent: Intent, missing_fields: list[InformationField]) -> str:
    match intent:
        case Intent.AVAILABILITY_CHECK:
            return build_ask_data_availability(missing_fields=missing_fields)
        case Intent.BOOKING_REQUEST:
            return build_ask_data_booking_request(missing_fields=missing_fields)
        case Intent.BOOKING_CANCELLATION:
            return build_ask_data_cancellation(missing_fields=missing_fields)


def build_ask_data_cancellation(missing_fields: list[InformationField]) -> str:
    retval = DefaultPhrases.CANCELLATION_ASK_FOR_DATA
    if InformationField.LAST_NAME in missing_fields:
        return retval + f" {DefaultPhrases.ASK_LAST_NAME}"
    if InformationField.EMAIL in missing_fields:
        return retval + f" {DefaultPhrases.ASK_EMAIL}"
    if InformationField.CHECK_IN in missing_fields:
        return retval + f" {DefaultPhrases.ASK_CHECK_IN}"

def build_ask_data_booking_request(missing_fields: list[InformationField]) -> str:
    retval = DefaultPhrases.BOOKING_ASK_FOR_DATA
    basic_data = build_ask_data_availability(missing_fields=missing_fields, called_from_booking=True)
    retval += basic_data
    if basic_data != "":
        return retval
    if InformationField.FIRST_NAME in missing_fields and InformationField.LAST_NAME in missing_fields:
        retval += f" {DefaultPhrases.ASK_FIRST_AND_LAST_NAME}"
        return retval
    if InformationField.FIRST_NAME in missing_fields:
        return retval + f" {DefaultPhrases.ASK_FIRST_NAME}"
    if InformationField.LAST_NAME in missing_fields:
        return retval + f" {DefaultPhrases.ASK_LAST_NAME}"
    if InformationField.BREAKFAST in missing_fields:
        return retval + f" {DefaultPhrases.ASK_BREAKFAST}"
    if InformationField.EMAIL in missing_fields:
        return retval + f" {DefaultPhrases.ASK_EMAIL}"



def build_ask_data_availability(missing_fields: list[InformationField], called_from_booking=False) -> str:
    retval = ""
    if not called_from_booking:
        retval += DefaultPhrases.AVAILABILITY_ASK_FOR_DATA
    if InformationField.CHECK_IN in missing_fields and InformationField.CHECK_OUT in missing_fields:
        retval += f" {DefaultPhrases.ASK_CHECK_IN_AND_CHECK_OUT}"
        return retval
    if InformationField.CHECK_IN in missing_fields:
        return retval + f" {DefaultPhrases.ASK_CHECK_IN}"
    if InformationField.CHECK_OUT in missing_fields:
        return retval + f" {DefaultPhrases.ASK_CHECK_OUT}"
    if InformationField.ACCESSIBLE in missing_fields:
        return retval + f" {DefaultPhrases.ASK_ACCESABILITY}"
    if InformationField.GUEST_COUNT in missing_fields:
        return retval + f" {DefaultPhrases.ASK_NUMBER_GUESTS}"

    return ""



