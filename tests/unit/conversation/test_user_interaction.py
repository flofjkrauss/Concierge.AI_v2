from datetime import date

import pytest

from configuration.application import ApplicationSettings
from conversation.entities.interaction_response import (
    AskConfirmationResponse,
    AvailabilityResponse,
    BookingResponse,
    EmptyInteractionResponse,
    ErrorResponse,
    GreetingResponse,
    InformationResponse,
    InteractionResponse,
)
from conversation.user_interaction import UserInteraction, _display_value
from conversation.value_object.action import Action
from conversation.value_object.default_phrases import DefaultPhrases
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.services.find_matching_rooms import MatchResponse


def test_parse_message_trims_whitespace() -> None:
    interaction = UserInteraction()

    message = interaction.parse_message("  Hello  ")

    assert message is not None
    assert message.content == "Hello"
    assert message.original_content == "Hello"


def test_parse_message_rejects_content_above_limit() -> None:
    interaction = UserInteraction()
    interaction.settings = ApplicationSettings(msg_max_length=3)

    assert interaction.parse_message("four") is None


def test_parse_message_accepts_content_at_limit() -> None:
    interaction = UserInteraction()
    interaction.settings = ApplicationSettings(msg_max_length=4)

    assert interaction.parse_message("four") is not None


def test_standard_responses_expose_expected_session_state() -> None:
    interaction = UserInteraction()

    greeting = interaction.display_greeting(
        Intent.CONVERSATION_INITIATION,
        "session-1",
    )
    error = interaction.send_error_msg("invalid")
    empty = interaction.send_empty_response()

    assert greeting == GreetingResponse(
        True,
        DefaultPhrases.GREETING,
        "session-1",
    )
    assert error == ErrorResponse(True, DefaultPhrases.ERROR_MESSAGE, "invalid")
    assert empty == EmptyInteractionResponse()


def test_build_response_dispatches_selected_action(monkeypatch) -> None:
    interaction = UserInteraction()
    expected = InteractionResponse(True, "custom")

    def handler(*, intent: Intent, data: object) -> InteractionResponse:
        assert intent is Intent.BOOKING_CHECK
        assert data == {"booking_id": "booking-1"}
        return expected

    monkeypatch.setattr(
        interaction,
        "display_booking",
        handler,
    )

    result = interaction.build_response(
        Action.DISPLAY_BOOKING,
        Intent.BOOKING_CHECK,
        {"booking_id": "booking-1"},
    )

    assert result is expected


def test_ask_for_data_builds_availability_prompt() -> None:
    interaction = UserInteraction()
    missing_fields = [InformationField.CHECK_IN]

    response = interaction.ask_for_data(
        Intent.AVAILABILITY_CHECK,
        missing_fields,
    )

    assert isinstance(response, AvailabilityResponse)
    assert response.content is missing_fields
    assert DefaultPhrases.ASK_CHECK_IN in response.text


def test_ask_for_data_builds_information_topics_card_response() -> None:
    response = UserInteraction().ask_for_data(
        Intent.INFORMATION_REQUEST,
        [InformationField.INFORMATION_TOPIC],
    )

    assert isinstance(response, InformationResponse)
    assert response.text == DefaultPhrases.ASK_INFORMATION_TOPIC


def test_ask_for_confirmation_keeps_domain_data() -> None:
    interaction = UserInteraction()
    domain_data = object()

    response = interaction.ask_for_confirmation(
        Intent.BOOKING_REQUEST,
        domain_data,
    )

    assert isinstance(response, AskConfirmationResponse)
    assert response.data is domain_data
    assert response.text == DefaultPhrases.ASK_CONFIRMATION_BOOKING


@pytest.mark.parametrize(
    ("field", "date_role"),
    [
        (InformationField.CHECK_IN, "check-in"),
        (InformationField.CHECK_OUT, "check-out"),
    ],
)
def test_report_reused_date_names_existing_date_role(
    field: InformationField,
    date_role: str,
) -> None:
    response = UserInteraction().report_reused_date(
        Intent.BOOKING_REQUEST,
        field,
    )

    assert response == InteractionResponse(
        True,
        f"That date is already being used as your {date_role} date.",
    )


def test_report_email_in_use_keeps_chat_open() -> None:
    response = UserInteraction().report_email_in_use(
        Intent.BOOKING_REQUEST,
        None,
    )

    assert response == ErrorResponse(
        True,
        DefaultPhrases.EMAIL_IN_USE,
        "Email address is already in use by another guest",
    )


def test_display_info_requires_text() -> None:
    interaction = UserInteraction()

    response = interaction.display_info(Intent.INFORMATION_REQUEST, "Free Wi-Fi")

    assert response == InformationResponse(True, "Free Wi-Fi")
    with pytest.raises(TypeError, match="Expected string"):
        interaction.display_info(Intent.INFORMATION_REQUEST, object())


def test_display_availability_maps_matching_rooms(
    booking_request: BookingRequest,
    room: Room,
) -> None:
    interaction = UserInteraction()
    match_response = MatchResponse(booking_request, [room])

    response = interaction.display_availability(
        Intent.AVAILABILITY_CHECK,
        match_response,
    )

    assert isinstance(response, AvailabilityResponse)
    assert response.text == DefaultPhrases.AVAILABLE_ROOM_CATEGORIES
    assert len(response.content.rooms) == 1
    assert response.content.rooms[0].category == room.category


def test_display_availability_rejects_non_room_entries(
    booking_request: BookingRequest,
) -> None:
    interaction = UserInteraction()
    match_response = MatchResponse(
        booking_request,
        ["not-a-room"],  # type: ignore[list-item]
    )

    with pytest.raises(TypeError, match="Expected Room objects"):
        interaction.display_availability(
            Intent.AVAILABILITY_CHECK,
            match_response,
        )


def test_display_booking_distinguishes_missing_and_found_booking() -> None:
    interaction = UserInteraction()
    booking_data = object()

    missing = interaction.display_booking(Intent.BOOKING_CHECK, None)
    found = interaction.display_booking(Intent.BOOKING_CHECK, booking_data)

    assert missing == BookingResponse(
        True,
        DefaultPhrases.BOOKING_NOT_FOUND,
        None,
    )
    assert isinstance(found, BookingResponse)
    assert found.content is booking_data
    assert found.text == DefaultPhrases.DISPLAY_BOOKING


def test_ask_intent_returns_retry_prompt() -> None:
    response = UserInteraction().ask_intent(Intent.UNKNOWN, None)

    assert response == InteractionResponse(True, DefaultPhrases.ASK_INTENT)


def test_build_response_rejects_unsupported_action() -> None:
    with pytest.raises(ValueError, match="Unsupported interaction action"):
        UserInteraction().build_response(
            object(),  # type: ignore[arg-type]
            Intent.UNKNOWN,
            None,
        )


@pytest.mark.parametrize(
    ("intent", "response_type"),
    [
        (Intent.BOOKING_CHECK, BookingResponse),
        (Intent.BOOKING_REQUEST, BookingResponse),
        (Intent.BOOKING_CANCELLATION, BookingResponse),
        (Intent.UNKNOWN, InteractionResponse),
    ],
)
def test_ask_for_data_selects_intent_specific_response_type(
    intent: Intent,
    response_type: type[InteractionResponse],
) -> None:
    response = UserInteraction().ask_for_data(
        intent,
        [InformationField.EMAIL],
    )

    assert type(response) is response_type
    assert response.session_active is True


def test_information_change_prompt_formats_one_or_multiple_replacements() -> None:
    interaction = UserInteraction()

    single = interaction.ask_for_information_change(
        Intent.BOOKING_REQUEST,
        {InformationField.ACCESSIBLE: (False, True)},
    )
    multiple = interaction.ask_for_information_change(
        Intent.BOOKING_REQUEST,
        {
            "check_in": (date(2030, 6, 10), date(2030, 6, 11)),
            InformationField.GUEST_COUNT: (1, 2),
        },
    )

    assert single.text == (
        "Should the existing value be replaced? accessible requested: no to yes."
    )
    assert "Should these existing values be replaced?" in multiple.text
    assert "check in: 2030-06-10 to 2030-06-11" in multiple.text
    assert "guest count: 1 to 2" in multiple.text


@pytest.mark.parametrize(
    "data",
    [None, {}, {"unknown": (1, 2)}, {InformationField.EMAIL: "old to new"}],
)
def test_information_change_prompt_rejects_invalid_replacements(data: object) -> None:
    with pytest.raises(TypeError, match="Information-change|Invalid information-change"):
        UserInteraction().ask_for_information_change(
            Intent.BOOKING_REQUEST,
            data,
        )


@pytest.mark.parametrize(
    ("field", "expected_fragment"),
    [
        (InformationField.CHECK_IN, "check-in date"),
        (InformationField.CHECK_OUT, "check-out date"),
    ],
)
def test_report_invalid_date_explains_required_date_order(
    field: InformationField,
    expected_fragment: str,
) -> None:
    response = UserInteraction().report_invalid_date(
        Intent.BOOKING_REQUEST,
        field,
    )

    assert expected_fragment in response.text
    assert response.session_active is True


def test_date_reports_reject_non_date_fields() -> None:
    interaction = UserInteraction()
    with pytest.raises(TypeError, match="Invalid-date response"):
        interaction.report_invalid_date(Intent.BOOKING_REQUEST, InformationField.EMAIL)
    with pytest.raises(TypeError, match="Reused-date response"):
        interaction.report_reused_date(Intent.BOOKING_REQUEST, InformationField.EMAIL)


def test_display_availability_handles_no_vacancy_and_preserves_request(
    booking_request: BookingRequest,
) -> None:
    response = UserInteraction().display_availability(
        Intent.AVAILABILITY_CHECK,
        MatchResponse(booking_request, []),
    )

    assert response.text == DefaultPhrases.NO_VACANCY
    assert response.content.request is not None
    assert response.content.request.check_in == booking_request.stay_period.check_in
    assert response.content.rooms == []


def test_display_availability_requires_domain_result() -> None:
    with pytest.raises(TypeError, match="containing a 'rooms' attribute"):
        UserInteraction().display_availability(Intent.AVAILABILITY_CHECK, None)


@pytest.mark.parametrize("session_id", [None, "", "   "])
def test_display_greeting_requires_nonempty_session_id(session_id: object) -> None:
    with pytest.raises(TypeError, match="valid session ID"):
        UserInteraction().display_greeting(
            Intent.CONVERSATION_INITIATION,
            session_id,
        )


@pytest.mark.parametrize(
    ("value", "display"),
    [(True, "yes"), (False, "no"), (date(2030, 6, 10), "2030-06-10"), (3, "3")],
)
def test_display_value_formats_guest_facing_values(value: object, display: str) -> None:
    assert _display_value(value) == display


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        (Intent.BOOKING_REQUEST, DefaultPhrases.ABORT_BOOKING_REQUEST),
        (Intent.BOOKING_CANCELLATION, DefaultPhrases.ABORT_CANCEL_REQUEST),
        (Intent.UNKNOWN, DefaultPhrases.GENERIC_ASK_FOR_CONFIRMATION),
    ],
)
def test_declined_confirmation_uses_intent_specific_follow_up(
    intent: Intent,
    expected: DefaultPhrases,
) -> None:
    response = UserInteraction().ask_further_intent(intent, None)

    assert response == InteractionResponse(True, expected)
