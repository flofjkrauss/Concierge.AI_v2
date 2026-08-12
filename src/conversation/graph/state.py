"""Typed state for the in-memory LangGraph conversation workflow."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, NotRequired, TypedDict

from conversation.entities.information import Information
from conversation.entities.interaction_response import InteractionResponse
from conversation.entities.message import Message
from conversation.graph.reducers import merge_information, merge_messages
from conversation.value_object.action import Action
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


class MessageRole(StrEnum):
    """Conversation side associated with a history entry."""

    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    """A repository ``Message`` plus the conversation side that produced it."""

    role: MessageRole
    message: Message

    @property
    def message_id(self) -> str:
        """Expose the wrapped ID for the message-history reducer."""

        return self.message.message_id


class DomainOperation(StrEnum):
    """Domain operations that can be selected by conversation routing."""

    FIND_AVAILABILITY = "find_availability"
    CHECK_BOOKING_AVAILABILITY = "check_booking_availability"
    GET_BOOKING = "get_booking"
    CREATE_BOOKING = "create_booking"
    CANCEL_BOOKING = "cancel_booking"
    GET_INFORMATION = "get_information"
    PREVIEW_BOOKING = "preview_booking"


class ExpectedInteractionKind(StrEnum):
    """Structured user interactions understood by the graph."""

    BOOKING_CONFIRMATION = "booking_confirmation"
    CANCELLATION_CONFIRMATION = "cancellation_confirmation"
    INFORMATION_CHANGE_CONFIRMATION = "information_change_confirmation"


@dataclass(frozen=True, slots=True)
class ExpectedInteraction:
    """A pending confirmation and its optional domain operation."""

    kind: ExpectedInteractionKind
    intent: Intent
    operation: DomainOperation | None


class ConfirmationOutcome(StrEnum):
    """Result of interpreting a message while confirmation is pending."""

    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CHANGED = "changed"
    INFORMATION_CHANGE_CONFIRMED = "information_change_confirmed"
    INFORMATION_CHANGE_DECLINED = "information_change_declined"
    INTERRUPTED = "interrupted"
    UNCLEAR = "unclear"


class ConversationState(TypedDict):
    """Authoritative state persisted per LangGraph ``thread_id``."""

    # Persistent conversation state
    initialized: bool
    session_id: str
    session_active: bool
    language: str | None
    message_history: Annotated[list[ConversationMessage], merge_messages]
    collected_information: Annotated[
        dict[InformationField, Information],
        merge_information,
    ]
    current_intent: Intent
    last_intent_fulfilled: bool
    missing_fields: list[InformationField]
    unknown_counter: int
    expected_interaction: ExpectedInteraction | None
    pending_information_changes: dict[InformationField, Information]
    availability_requested: bool
    last_booking_check_in: Information | None
    validated_availability_signature: (
        tuple[str, str, int | None, bool | None, str | None] | None
    )

    # Transient current-turn state
    incoming_message: str | None
    parsed_message: Message | None
    translated_message: Message | None
    detected_intent: Intent | None
    extracted_information: list[Information]
    changed_fields: list[InformationField]
    action: Action | None
    domain_operation: DomainOperation | None
    domain_data: object | None
    response: InteractionResponse | None
    response_in_domain_language: str | None
    confirmation_outcome: ConfirmationOutcome | None
    termination_requested: bool
    next_missing_field: InformationField | None


class ConversationInput(TypedDict):
    """Accepted input for a new session or one conversation turn."""

    incoming_message: str | None
    session_id: NotRequired[str]
    session_active: NotRequired[bool]
    language: NotRequired[str | None]


class ConversationOutput(TypedDict):
    """Public result returned by the compiled graph."""

    response: InteractionResponse | None
    session_active: bool
