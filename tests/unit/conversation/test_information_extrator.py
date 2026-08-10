import pytest

from conversation.entities.message import Message
from conversation.information_extrator import DebugTestInput, InformationExtractor
from conversation.value_object.information_fields import InformationField


@pytest.mark.parametrize("reply", ["yes", "no"])
def test_extract_ignores_plain_confirmation_replies(reply: str) -> None:
    assert InformationExtractor().extract(Message(reply, original_content=reply)) == []


@pytest.mark.parametrize(
    ("raw_message", "expected_fields"),
    [
        (
            DebugTestInput.AVAILABILIY_CHECK,
            [
                InformationField.GUEST_COUNT,
                InformationField.CHECK_OUT,
                InformationField.ACCESSIBLE,
                InformationField.CHECK_IN,
            ],
        ),
        (
            DebugTestInput.BOOKING_CHECK,
            [
                InformationField.LAST_NAME,
                InformationField.CHECK_IN,
                InformationField.EMAIL,
            ],
        ),
        (
            DebugTestInput.BOOKING_CANCELLATION,
            [
                InformationField.LAST_NAME,
                InformationField.CHECK_IN,
                InformationField.EMAIL,
            ],
        ),
        (
            DebugTestInput.INFORMATION_REQUEST,
            [InformationField.INFORMATION_TOPIC],
        ),
    ],
)
def test_extract_returns_fields_for_debug_scenarios(
    raw_message: str,
    expected_fields: list[InformationField],
) -> None:
    extracted = InformationExtractor().extract(
        Message(raw_message, original_content=raw_message)
    )

    assert [information.information_field for information in extracted] == (
        expected_fields
    )
    assert all(information.is_valid() for information in extracted)


def test_extract_returns_complete_debug_booking_data() -> None:
    extracted = InformationExtractor().extract(
        Message(
            DebugTestInput.BOOKING_REQUEST,
            original_content=DebugTestInput.BOOKING_REQUEST,
        )
    )

    assert {information.information_field for information in extracted} == {
        InformationField.FIRST_NAME,
        InformationField.LAST_NAME,
        InformationField.GUEST_COUNT,
        InformationField.CHECK_OUT,
        InformationField.ACCESSIBLE,
        InformationField.CHECK_IN,
        InformationField.BREAKFAST,
        InformationField.EMAIL,
        InformationField.PREFERRED_LANG,
        InformationField.ROOM_CATEGORY,
        InformationField.PHONE,
    }


def test_extract_returns_no_data_for_unknown_message() -> None:
    assert (
        InformationExtractor().extract(
            Message("something else", original_content="something else")
        )
        == []
    )
