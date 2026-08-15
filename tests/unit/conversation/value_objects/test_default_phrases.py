import pytest

from conversation.value_object.action import Action
from conversation.value_object.default_phrases import (
    DefaultPhrases,
    _build_missing_fields_fallback,
    build,
    build_ask_confirmation,
    build_ask_data_booking_check,
    build_ask_data_booking_request,
    build_ask_data_cancellation,
    build_confirmation_declined,
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


def test_information_prompt_lists_supported_topics() -> None:
    result = build(
        Action.ASK_FOR_DATA,
        Intent.INFORMATION_REQUEST,
        [InformationField.INFORMATION_TOPIC],
    )

    assert result == DefaultPhrases.ASK_INFORMATION_TOPIC
    assert result.startswith("(available_topics)")
    assert "\n- Arrival and departure:" in result
    assert "\n- Rooms and guest services:" in result
    assert "\n- Food and leisure:" in result
    assert "\n- Connectivity and transport:" in result
    assert "\n- Policies and local information:" in result


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
    result = build_ask_confirmation(
        Intent.BOOKING_REQUEST,
        [InformationField.EMAIL],
    )

    assert "still need the following information" in result
    assert "your email address" in result


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        (Intent.BOOKING_REQUEST, DefaultPhrases.ABORT_BOOKING_REQUEST),
        (Intent.BOOKING_CANCELLATION, DefaultPhrases.ABORT_CANCEL_REQUEST),
        (Intent.UNKNOWN, DefaultPhrases.GENERIC_ASK_FOR_CONFIRMATION),
    ],
)
def test_confirmation_declined_prompt_matches_intent(
    intent: Intent,
    expected: DefaultPhrases,
) -> None:
    assert build_confirmation_declined(intent, []) == expected


@pytest.mark.parametrize(
    ("missing_field", "question"),
    [
        (InformationField.LAST_NAME, DefaultPhrases.ASK_LAST_NAME),
        (InformationField.EMAIL, DefaultPhrases.ASK_EMAIL),
        (InformationField.CHECK_IN, DefaultPhrases.ASK_CHECK_IN),
    ],
)
def test_booking_check_prompt_asks_for_lookup_identity(
    missing_field: InformationField,
    question: DefaultPhrases,
) -> None:
    assert build_ask_data_booking_check([missing_field]) == (
        f"{DefaultPhrases.BOOKING_CHECK_ASK_FOR_DATA} {question}"
    )


def test_booking_prompt_asks_for_full_guest_identity_at_once() -> None:
    result = build_ask_data_booking_request(
        [
            InformationField.FIRST_NAME,
            InformationField.LAST_NAME,
            InformationField.EMAIL,
        ]
    )

    assert result == (
        f"{DefaultPhrases.BOOKING_ASK_FOR_DATA} {DefaultPhrases.ASK_GUEST_DETAILS}"
    )


def test_phrase_builder_uses_safe_fallback_for_unknown_action() -> None:
    assert (
        build(
            object(),  # type: ignore[arg-type]
            Intent.UNKNOWN,
            [],
        )
        == DefaultPhrases.ASK_INTENT
    )


def test_missing_fields_fallback_names_fields_and_handles_empty_list() -> None:
    assert _build_missing_fields_fallback([]) == DefaultPhrases.ASK_INTENT

    result = _build_missing_fields_fallback(
        [InformationField.PHONE, InformationField.ROOM_CATEGORY]
    )

    assert "your phone number" in result
    assert "your preferred room category" in result


def test_lookup_and_cancellation_prompts_fallback_for_unexpected_field() -> None:
    lookup = build_ask_data_booking_check([InformationField.PHONE])
    cancellation = build_ask_data_cancellation([InformationField.PHONE])

    assert "your phone number" in lookup
    assert "your phone number" in cancellation
