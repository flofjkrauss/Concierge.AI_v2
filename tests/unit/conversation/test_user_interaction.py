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
from conversation.user_interaction import UserInteraction
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
    assert error == ErrorResponse(False, DefaultPhrases.ERROR_MESSAGE, "invalid")
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

    with pytest.raises(TypeError, match="Invalid object in list"):
        interaction.display_availability(
            Intent.AVAILABILITY_CHECK,
            match_response,
        )


def test_display_booking_distinguishes_missing_and_found_booking() -> None:
    interaction = UserInteraction()
    booking_data = object()

    missing = interaction.display_booking(Intent.BOOKING_CHECK, None)
    found = interaction.display_booking(Intent.BOOKING_CHECK, booking_data)

    assert missing == InteractionResponse(
        True,
        DefaultPhrases.BOOKING_NOT_FOUND,
    )
    assert isinstance(found, BookingResponse)
    assert found.content is booking_data
    assert found.text == DefaultPhrases.DISPLAY_BOOKING


def test_ask_intent_returns_retry_prompt() -> None:
    response = UserInteraction().ask_intent(Intent.UNKNOWN, None)

    assert response == InteractionResponse(True, DefaultPhrases.ASK_INTENT)
