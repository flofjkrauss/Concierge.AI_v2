from __future__ import annotations
from enum import StrEnum


from conversation.value_object.information_fields import InformationField
from conversation.value_object.action import Action
from conversation.value_object.intent import Intent


class DefaultPhrases(StrEnum):
    GREETING = "Welcome! How can I help you?"
    CONFIRM_BOOKING = "Please check booking Details and click on confirm"
    CANCEL_BOOKING = "Are you sure, you want to cancel this booking?"
    UNKNOWN_INTENT = "Unfortunately, I was not able to understand you. Please try again."
    ERROR_MESSAGE = "Something went terribly wrong!"
    AVAILABLE_ROOM_CATEGORIES = "According to your request, these room categories are available...."
    NO_VACANCY = "Unfortunately, we have no vacancy in the requested stay period."
    AVAILABILITY_ASK_FOR_DATA = "To offer possible booking options, I need to collect additional data. Please tell me:"
    ASK_CHECK_IN = "When would you like to check in?"
    ASK_CHECK_OUT = "When yould you like to check out?"
    ASK_CHECK_IN_AND_CHECK_OUT = "During what timeframe may we welcome you?"
    ASK_ACCESABILITY = "Do you need an accessible room?"
    ASK_NUMBER_GUESTS = "How many people are you?"



def build(action: Action, intent: Intent, missing_fields: list[InformationField]) -> str:
    match action:
        case Action.ASK_FOR_DATA:
            return build_ask_data(intent=intent, missing_fields=missing_fields)

def build_ask_data(intent: Intent, missing_fields: list[InformationField]) -> str:
    match intent:
        case Intent.AVAILABILITY_CHECK:
            return build_ask_data_availability(missing_fields=missing_fields)


def build_ask_data_availability(missing_fields: list[InformationField]) -> str:
    retval = DefaultPhrases.AVAILABILITY_ASK_FOR_DATA
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



