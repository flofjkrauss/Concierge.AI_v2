from datetime import UTC, date, datetime

import pytest

from conversation.value_object.information_fields import InformationField
from utils.information_validator import (
    INFORMATION_VALIDATORS,
    has_mail_format,
    is_boolean,
    is_date,
    is_information_topic,
    is_non_empty_string,
    is_person_name,
    is_positive_integer,
    is_room_category,
    is_yes_or_no,
)


def test_is_date_accepts_dates_and_datetimes() -> None:
    assert is_date(date(2030, 1, 1))
    assert is_date(datetime(2030, 1, 1, tzinfo=UTC))
    assert not is_date("2030-01-01")


@pytest.mark.parametrize("value", [1, 42])
def test_is_positive_integer_accepts_positive_integers(value: int) -> None:
    assert is_positive_integer(value)


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "1"])
def test_is_positive_integer_rejects_other_values(value: object) -> None:
    assert not is_positive_integer(value)


def test_is_boolean_accepts_only_booleans() -> None:
    assert is_boolean(True)
    assert is_boolean(False)
    assert not is_boolean(1)


def test_is_non_empty_string_trims_for_validation() -> None:
    assert is_non_empty_string(" value ")
    assert not is_non_empty_string("   ")
    assert not is_non_empty_string(1)


def test_has_mail_format_requires_string_with_at_marker() -> None:
    assert has_mail_format("alex@example.com")
    assert not has_mail_format("alex.example.com")
    assert not has_mail_format(1)


def test_validator_registry_covers_stable_information_fields() -> None:
    supported_fields = {
        InformationField.CHECK_IN,
        InformationField.CHECK_OUT,
        InformationField.GUEST_COUNT,
        InformationField.BREAKFAST,
        InformationField.ACCESSIBLE,
        InformationField.FIRST_NAME,
        InformationField.LAST_NAME,
        InformationField.EMAIL,
        InformationField.PREFERRED_LANG,
        InformationField.PHONE,
    }

    assert supported_fields <= INFORMATION_VALIDATORS.keys()


@pytest.mark.parametrize(
    "name",
    ["Alex", "Anne-Marie", "D'Angelo", "María José"],
)
def test_is_person_name_accepts_realistic_names(name: str) -> None:
    assert is_person_name(name)


@pytest.mark.parametrize(
    "value",
    [None, "A", "booking", "Alex_1", "123", "x" * 101],
)
def test_is_person_name_rejects_non_names(value: object) -> None:
    assert not is_person_name(value)


def test_confirmation_validator_accepts_only_canonical_values() -> None:
    assert is_yes_or_no("yes")
    assert is_yes_or_no("no")
    assert not is_yes_or_no("Yes")
    assert not is_yes_or_no(True)


def test_topic_and_room_category_validators_use_domain_enums() -> None:
    assert is_information_topic("wifi")
    assert not is_information_topic("spa")
    assert not is_information_topic(1)
    assert is_room_category("double")
    assert not is_room_category("suite")
    assert not is_room_category(1)


def test_validator_registry_covers_every_information_field() -> None:
    assert set(INFORMATION_VALIDATORS) == set(InformationField)
