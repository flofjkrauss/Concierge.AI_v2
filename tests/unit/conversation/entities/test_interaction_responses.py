from api.schemas.availability_schema import (
    AvailabilityResponse as ApiAvailabilityResponse,
)
from conversation.entities.interaction_response import (
    AvailabilityResponse,
    EmptyInteractionResponse,
    ErrorResponse,
    GreetingResponse,
)
from conversation.value_object.default_phrases import DefaultPhrases


def test_empty_response_keeps_session_active() -> None:
    assert EmptyInteractionResponse() == EmptyInteractionResponse(
        session_active=True,
        text="",
    )


def test_error_response_keeps_reason() -> None:
    response = ErrorResponse(session_active=False, text="Error", reason="invalid")

    assert response.reason == "invalid"


def test_greeting_response_uses_default_phrase() -> None:
    response = GreetingResponse(
        session_active=True,
        text=DefaultPhrases.GREETING,
        session_id="session-1",
    )

    assert response.text == DefaultPhrases.GREETING
    assert response.session_id == "session-1"


def test_availability_response_keeps_structured_content() -> None:
    content = ApiAvailabilityResponse(rooms=[])

    response = AvailabilityResponse(True, "Available", content)

    assert response.content is content
