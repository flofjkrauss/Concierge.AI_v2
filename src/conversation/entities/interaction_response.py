"""conversation entity."""
from dataclasses import dataclass

from api.schemas.availability_schema import (
    AvailabilityResponse as api_availability_response,
)
from conversation.value_object.default_phrases import DefaultPhrases
from domain.value_objects.information_topic import InformationTopic


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
    topic: InformationTopic

@dataclass(slots=True)
class AvailabilityResponse(InteractionResponse):
    """availability request response"""
    content: api_availability_response

@dataclass(slots=True)
class BookingResponse(InteractionResponse):
    """booking request response"""
    content: api_availability_response

@dataclass(slots=True)
class GreetingResponse(InteractionResponse):
    """booking request response"""
    text: str = DefaultPhrases.GREETING
