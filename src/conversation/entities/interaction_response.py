"""conversation entity."""
from dataclasses import dataclass
from enum import StrEnum

from api.schemas.availability_schema import (
    AvailabilityResponse as api_availability_response,
)
from api.schemas.booking_schema import BookingResponse as api_booking_response

class UserOptions(StrEnum):
    """Result of interpreting a message while confirmation is pending."""

    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CHANGED = "changed"
    INTERRUPTED = "interrupted"
    UNCLEAR = "unclear"

@dataclass(slots=True)
class InteractionResponse:
    """interaction response object"""

    session_active: bool
    text: str

@dataclass(slots=True)
class EmptyInteractionResponse(InteractionResponse):
    """empte response object if an empty message was received"""
    session_active: bool = True
    text: str = ""

@dataclass(slots=True)
class ErrorResponse(InteractionResponse):
    """error response"""
    reason: str

@dataclass(slots=True)
class InformationResponse(InteractionResponse):
    """information request response"""

@dataclass(slots=True)
class AvailabilityResponse(InteractionResponse):
    """availability request response"""
    content: api_availability_response

@dataclass(slots=True)
class BookingResponse(InteractionResponse):
    """booking request response"""
    content: api_booking_response

@dataclass(slots=True)
class GreetingResponse(InteractionResponse):
    """booking request response"""
    session_id: str

@dataclass(slots=True)
class AskConfirmationResponse(InteractionResponse):
    """ ask for confirmation response """
    options: list[UserOptions]
    
