"""conversation entity."""
from dataclasses import dataclass
from enum import StrEnum
from datetime import date

from api.schemas.availability_schema import (
    AvailabilityResponse as api_availability_response,
)
from api.schemas.booking_schema import BookingResponse as api_booking_response

from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.booking_status import BookingStatus


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
    data: api_booking_response

@dataclass(slots=True, frozen=True)
class BookingResponseObject:
    status: BookingStatus
    room_category: str
    guest_count: int
    check_in: date
    check_out: date
    total_prize: int
    accessible: bool
    breakfast: bool
    first_name: str
    last_name: str
    email: str
    phone: str | None = None

@dataclass(slots=True, frozen=True)
class BookingPreview:
    first_name: str
    last_name: str
    email: str
    check_in: date
    check_out: date
    guest_count: int
    room_category: RoomCategory
    breakfast_included: bool
    total_price: Money
