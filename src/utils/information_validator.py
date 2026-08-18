import re
from collections.abc import Callable
from datetime import date

from conversation.value_object.information_fields import InformationField
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.room_category import RoomCategory

InformationValidator = Callable[[object], bool]


_EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)
_PERSON_NAME_PATTERN = re.compile(
    r"^[^\W\d_]+(?:[-' ][^\W\d_]+)*$",
    re.UNICODE,
)
_NON_NAME_WORDS = frozenset(
    {
        "i",
        "we",
        "you",
        "need",
        "want",
        "would",
        "like",
        "room",
        "rooms",
        "hotel",
        "guest",
        "guests",
        "book",
        "booking",
        "reservation",
    }
)

def is_date(value: object) -> bool:
    return isinstance(value, date)


def is_positive_integer(value: object) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
    )


def is_boolean(value: object) -> bool:
    return isinstance(value, bool)


def is_non_empty_string(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
    )


def is_person_name(value: object) -> bool:
    if not isinstance(value, str):
        return False

    normalized = value.strip()
    return (
        1 < len(normalized) <= 100
        and normalized.casefold() not in _NON_NAME_WORDS
        and _PERSON_NAME_PATTERN.fullmatch(normalized) is not None
    )

def has_mail_format(value: object) -> bool:
    if not isinstance(value, str):
        return False
    
    return _EMAIL_PATTERN.fullmatch(value.strip()) is not None

def is_yes_or_no(value: object) -> bool:
    if not isinstance(value, str):
        return False

    return any([
        value == "yes",
        value == "no"
        ])


def is_information_topic(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        InformationTopic(value)
    except ValueError:
        return False
    return True


def is_room_category(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        RoomCategory(value)
    except ValueError:
        return False
    return True

INFORMATION_VALIDATORS: dict[
    InformationField,
    InformationValidator,
] = {
    InformationField.CHECK_IN: is_date,
    InformationField.CHECK_OUT: is_date,
    InformationField.GUEST_COUNT: is_positive_integer,
    InformationField.BREAKFAST: is_boolean,
    InformationField.ACCESSIBLE: is_boolean,
    InformationField.FIRST_NAME: is_person_name,
    InformationField.LAST_NAME: is_person_name,
    InformationField.EMAIL: has_mail_format,
    InformationField.PREFERRED_LANG: is_non_empty_string,
    InformationField.PHONE: is_non_empty_string,
    InformationField.INFORMATION_TOPIC: is_information_topic,
    InformationField.ROOM_CATEGORY: is_room_category,
    InformationField.CONFIRMATION: is_yes_or_no,
}
