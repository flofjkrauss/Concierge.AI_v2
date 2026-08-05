from collections.abc import Callable
from datetime import date

from conversation.value_object.information_fields import InformationField

InformationValidator = Callable[[object], bool]

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

def has_mail_format(value: object) -> bool:
    if isinstance(value, str):
        # TODO: replace this with a proper regex
        return value.find("@") != -1
    return False

INFORMATION_VALIDATORS: dict[
    InformationField,
    InformationValidator,
] = {
    InformationField.CHECK_IN: is_date,
    InformationField.CHECK_OUT: is_date,
    InformationField.GUEST_COUNT: is_positive_integer,
    InformationField.BREAKFAST: is_boolean,
    InformationField.ACCESSIBLE: is_boolean,
    InformationField.FIRST_NAME: is_non_empty_string,
    InformationField.LAST_NAME: is_non_empty_string,
    InformationField.EMAIL: has_mail_format,
    InformationField.BOOKING_ID: is_non_empty_string,
    InformationField.PREFERRED_LANG: is_non_empty_string,
    InformationField.PHONE: is_non_empty_string,
}