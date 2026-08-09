from datetime import UTC, datetime

import pytest

from conversation.entities.information import Information
from conversation.value_object.information_fields import InformationField


def test_information_accepts_valid_registered_content() -> None:
    information = Information(InformationField.GUEST_COUNT, 2)

    assert information.content == 2
    assert information.is_valid()
    assert information.created_at.tzinfo is not None
    assert information.information_id


def test_information_rejects_blank_id() -> None:
    with pytest.raises(ValueError, match="information_id must not be empty"):
        Information(InformationField.FIRST_NAME, "Alex", information_id=" ")


def test_information_rejects_unknown_field() -> None:
    with pytest.raises(TypeError, match="unregistered information field"):
        Information("first_name", "Alex")  # type: ignore[arg-type]


def test_information_rejects_invalid_content_for_field() -> None:
    with pytest.raises(ValueError, match="invalid for information field"):
        Information(InformationField.GUEST_COUNT, True)


def test_information_requires_timezone_aware_creation_time() -> None:
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        Information(
            InformationField.FIRST_NAME,
            "Alex",
            created_at=datetime(2030, 1, 1, tzinfo=UTC).replace(tzinfo=None),
        )
