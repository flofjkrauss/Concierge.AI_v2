
from configuration.application import ApplicationSettings
from conversation.entities.interaction_response import (
    EmptyInteractionResponse,
    ErrorResponse,
    InteractionResponse,
)
from conversation.user_interaction import UserInteraction
from conversation.value_object.action import Action
from conversation.value_object.default_phrases import DefaultPhrases
from conversation.value_object.intent import Intent


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

    session = interaction.send_session_id("session-1")
    error = interaction.send_error_msg("invalid")
    empty = interaction.send_empty_response()

    assert session == InteractionResponse(True, "session-1")
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
