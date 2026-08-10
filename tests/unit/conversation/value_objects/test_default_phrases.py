import pytest

from conversation.value_object.action import Action
from conversation.value_object.default_phrases import (
    DefaultPhrases,
    build,
    build_ask_confirmation,
    build_ask_data_booking_request,
    build_ask_data_cancellation,
)
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


def test_build_asks_for_both_stay_dates() -> None:
    result = build(
        Action.ASK_FOR_DATA,
        Intent.AVAILABILITY_CHECK,
        [InformationField.CHECK_IN, InformationField.CHECK_OUT],
    )

    assert result == (
        f"{DefaultPhrases.AVAILABILITY_ASK_FOR_DATA} "
        f"{DefaultPhrases.ASK_CHECK_IN_AND_CHECK_OUT}"
    )


@pytest.mark.parametrize(
    ("missing_field", "question"),
    [
        (InformationField.LAST_NAME, DefaultPhrases.ASK_LAST_NAME),
        (InformationField.EMAIL, DefaultPhrases.ASK_EMAIL),
        (InformationField.CHECK_IN, DefaultPhrases.ASK_CHECK_IN),
    ],
)
def test_cancellation_prompt_asks_for_next_missing_identity_field(
    missing_field: InformationField,
    question: DefaultPhrases,
) -> None:
    assert build_ask_data_cancellation([missing_field]) == (
        f"{DefaultPhrases.CANCELLATION_ASK_FOR_DATA} {question}"
    )


def test_booking_prompt_prioritizes_full_name() -> None:
    assert build_ask_data_booking_request(
        [InformationField.FIRST_NAME, InformationField.LAST_NAME]
    ) == (
        f"{DefaultPhrases.BOOKING_ASK_FOR_DATA} "
        f"{DefaultPhrases.ASK_FIRST_AND_LAST_NAME}"
    )


@pytest.mark.parametrize(
    ("missing_field", "question"),
    [
        (InformationField.CHECK_IN, DefaultPhrases.ASK_CHECK_IN),
        (InformationField.CHECK_OUT, DefaultPhrases.ASK_CHECK_OUT),
        (InformationField.ACCESSIBLE, DefaultPhrases.ASK_ACCESABILITY),
        (InformationField.GUEST_COUNT, DefaultPhrases.ASK_NUMBER_GUESTS),
    ],
)
def test_availability_prompt_asks_for_next_missing_field(
    missing_field: InformationField,
    question: DefaultPhrases,
) -> None:
    assert (
        build(
            Action.ASK_FOR_DATA,
            Intent.AVAILABILITY_CHECK,
            [missing_field],
        )
        == f"{DefaultPhrases.AVAILABILITY_ASK_FOR_DATA} {question}"
    )


@pytest.mark.parametrize(
    ("missing_field", "question"),
    [
        (InformationField.FIRST_NAME, DefaultPhrases.ASK_FIRST_NAME),
        (InformationField.LAST_NAME, DefaultPhrases.ASK_LAST_NAME),
        (InformationField.BREAKFAST, DefaultPhrases.ASK_BREAKFAST),
        (InformationField.EMAIL, DefaultPhrases.ASK_EMAIL),
    ],
)
def test_booking_prompt_asks_for_next_customer_or_booking_field(
    missing_field: InformationField,
    question: DefaultPhrases,
) -> None:
    assert build_ask_data_booking_request([missing_field]) == (
        f"{DefaultPhrases.BOOKING_ASK_FOR_DATA} {question}"
    )


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        (Intent.BOOKING_REQUEST, DefaultPhrases.ASK_CONFIRMATION_BOOKING),
        (
            Intent.BOOKING_CANCELLATION,
            DefaultPhrases.ASK_CONFIRMATION_CANCELLATION,
        ),
    ],
)
def test_confirmation_prompt_matches_side_effect(
    intent: Intent,
    expected: DefaultPhrases,
) -> None:
    assert build_ask_confirmation(intent, []) == expected


def test_confirmation_prompt_repeats_when_fields_are_reported_missing() -> None:
    assert (
        build_ask_confirmation(
            Intent.BOOKING_REQUEST,
            [InformationField.EMAIL],
        )
        == DefaultPhrases.REPEAT_ASK_CONFIRMATION
    )
