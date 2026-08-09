"""Conversation nodes and the small adapter to existing domain services."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from typing import Literal, Protocol, assert_never

from configuration.application import ApplicationSettings
from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.graph.state import (
    ConfirmationOutcome,
    ConversationMessage,
    ConversationState,
    DomainOperation,
    ExpectedInteraction,
    ExpectedInteractionKind,
    MessageRole,
)
from conversation.information_extrator import InformationExtractor
from conversation.intent_classifier import IntentClassifier
from conversation.models.translation.interface import TranslatorInterface
from conversation.user_interaction import UserInteraction
from conversation.value_object.action import Action
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent
from conversation.value_object.intent_information_mapping import (
    IntentInformationMapper,
)
from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.entities.customer import Customer
from domain.services.cancel_booking import cancel_booking_by_name
from domain.services.confirm_booking import confirm_booking
from domain.services.create_customer import create_customer
from domain.services.find_matching_rooms import find_matching_rooms
from domain.services.get_booking import get_booking_by_name
from domain.services.get_information import get_information
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.information_topic import InformationTopic
from observability.log_messages import LOG_MSG
from observability.utils.to_json import to_jsonable

StateUpdate = dict[str, object]


class ConversationDomainAdapter(Protocol):
    """Translate conversation data into calls to existing domain services."""

    def execute(
        self,
        operation: DomainOperation,
        information: Mapping[InformationField, Information],
    ) -> object:
        """Execute one previously selected domain operation."""


@dataclass(frozen=True, slots=True)
class DatabaseDomainAdapter:
    """Minimal adapter from collected fields to current domain-service calls."""

    database: DatabaseInterface

    def execute(
        self,
        operation: DomainOperation,
        information: Mapping[InformationField, Information],
    ) -> object:
        """Execute ``operation`` without moving business rules into LangGraph."""

        match operation:
            case DomainOperation.FIND_AVAILABILITY:
                (check_in, check_out, guest_count, accessible, breakfast) = _booking_request_tuple_from_information(information)
                return find_matching_rooms(
                    check_in=check_in,
                    check_out=check_out,
                    guest_count=guest_count,
                    breakfast=breakfast,
                    accessible=accessible,
                    database=self.database,
                )
            case DomainOperation.GET_BOOKING:
                last_name = _required_string(
                    information,
                    InformationField.LAST_NAME
                )
                email = _required_string(
                    information,
                    InformationField.EMAIL
                )
                check_in = _required_date(
                    information,
                    InformationField.CHECK_IN
                )
                return get_booking_by_name(
                    last_name=last_name,
                    email=email,
                    check_in=check_in,
                    database=self.database)
            case DomainOperation.CREATE_BOOKING:
                room_category = _required_string(
                    information,
                    InformationField.ROOM_CATEGORY
                )
                (check_in, check_out, guest_count, accessible, breakfast) = _booking_request_tuple_from_information(information)
                match_response =  find_matching_rooms(
                    check_in=check_in,
                    check_out=check_out,
                    guest_count=guest_count,
                    breakfast=breakfast,
                    accessible=accessible,
                    database=self.database,
                    room_category=room_category
                )
                if len(match_response.rooms) > 0:
                    customer = _create_customer_from_information(information, database=self.database)
                    return confirm_booking(
                        booking_request=match_response.request,
                        room_category=room_category,
                        customer=customer,
                        database=self.database
                    )
            case DomainOperation.CANCEL_BOOKING:
                last_name = _required_string(
                    information,
                    InformationField.LAST_NAME
                )
                email = _required_string(
                    information,
                    InformationField.EMAIL
                )
                check_in = _required_date(
                    information,
                    InformationField.CHECK_IN
                )
                return cancel_booking_by_name(
                    last_name=last_name,
                    email=email,
                    check_in=check_in,
                    database=self.database,
                )
            case DomainOperation.GET_INFORMATION:
                topic_value = _required_string(
                    information,
                    InformationField.INFORMATION_TOPIC,
                )
                return get_information(
                    topic=InformationTopic(topic_value),
                    database=self.database,
                )
            case _ as unreachable:
                assert_never(unreachable)


@dataclass(frozen=True, slots=True)
class ConversationNodes:
    """LangGraph node callables sharing application-scoped dependencies."""

    translator: TranslatorInterface
    intent_classifier: IntentClassifier
    information_extractor: InformationExtractor
    user_interaction: UserInteraction
    domain_adapter: ConversationDomainAdapter
    domain_language: str
    max_unknown_messages: int

    def begin_turn(self, state: ConversationState) -> StateUpdate:
        """Initialize a thread or normalize transient fields for a new turn."""

        updates: StateUpdate = {
            "parsed_message": None,
            "translated_message": None,
            "detected_intent": None,
            "extracted_information": [],
            "action": None,
            "domain_operation": None,
            "domain_data": None,
            "response": None,
            "response_in_domain_language": None,
            "confirmation_outcome": None,
            "termination_requested": False,
        }

        if not state.get("initialized", False):
            session_id = state.get("session_id")
            if session_id is None or not session_id.strip():
                raise ValueError("A new conversation requires a session_id")

            init_intent = Intent.CONVERSATION_INITIATION
            response = self.user_interaction.display_greeting(intent=init_intent, data=session_id)
            updates.update(
                {
                    "initialized": True,
                    "session_active": True,
                    "language": state.get("language"),
                    "message_history": [],
                    "collected_information": {},
                    "current_intent": init_intent,
                    "last_intent_fulfilled": False,
                    "missing_fields": [],
                    "unknown_counter": 0,
                    "expected_interaction": None,
                    "response": response,
                    "response_in_domain_language": response.text,
                }
            )
            return updates

        raw_message = state.get("incoming_message")
        if raw_message is None or not raw_message.strip():
            empty_response = self.user_interaction.send_empty_response()
            updates.update(
                {
                    "response": empty_response,
                    "response_in_domain_language": empty_response.text,
                    "session_active": empty_response.session_active,
                }
            )
            return updates

        parsed_message = self.user_interaction.parse_message(raw_message=raw_message)
        if parsed_message is None:
            error_response = self.user_interaction.send_error_msg(
                reason="Invalid message",
            )
            updates.update(
                {
                    "response": error_response,
                    "response_in_domain_language": error_response.text,
                    "session_active": error_response.session_active,
                }
            )
            return updates

        updates["parsed_message"] = parsed_message
        return updates


    def translate_input(self, state: ConversationState) -> StateUpdate:
        """Detect the session language once and translate input to English."""

        parsed_message = _required_message(state, "parsed_message")
        session_language = state.get("language")

        if session_language is None:
            detected_language = self.translator.determine(parsed_message).strip()
            session_language = detected_language or self.domain_language

        translated = parsed_message
        if session_language != self.domain_language:
            translated = self.translator.translate(
                parsed_message,
                target_lang=self.domain_language,
            )

        normalized = replace(
            translated,
            language=session_language,
        )
        return {
            "language": session_language,
            "translated_message": normalized,
        }

    def store_user_message(self, state: ConversationState) -> StateUpdate:
        """Append the normalized user message to authoritative history."""

        message = _required_message(state, "translated_message")
        return {
            "message_history": [
                ConversationMessage(role=MessageRole.USER, message=message)
            ]
        }

    def classify_intent(self, state: ConversationState) -> StateUpdate:
        """Classify intent using the current message plus both-sided history."""

        model_message = _contextual_model_message(state, self.domain_language)
        return {
            "detected_intent": self.intent_classifier.determine(
                message=model_message,
            )
        }

    def extract_information(self, state: ConversationState) -> StateUpdate:
        """Extract information on every turn, independently of intent."""

        message = _required_message(state, "translated_message")
        return {
            "extracted_information": self.information_extractor.extract(
                message=message,
            )
        }

    def update_progress(self, state: ConversationState) -> StateUpdate:
        """Merge extracted values and apply the consecutive-unknown rule."""

        extracted = state.get("extracted_information", [])
        intent = state.get("detected_intent") or Intent.UNKNOWN
        unknown_counter = state.get("unknown_counter", 0)
        current_message = state.get("translated_message")
        is_confirmation_reply = (
            state.get("expected_interaction") is not None
            and isinstance(current_message, Message)
            and _confirmation_decision(current_message.content) is not None
        )

        if intent == Intent.UNKNOWN and not extracted and not is_confirmation_reply:
            unknown_counter += 1
        else:
            unknown_counter = 0

        information_updates = {
            information.information_field: information for information in extracted
        }
        return {
            "collected_information": information_updates,
            "unknown_counter": unknown_counter,
            "termination_requested": (unknown_counter > self.max_unknown_messages),
        }

    def resolve_confirmation(self, state: ConversationState) -> StateUpdate:
        """Interpret a reply only when an explicit confirmation is pending."""

        expected = state.get("expected_interaction")
        if expected is None:
            raise ValueError("No confirmation is pending")

        changed_fields = {
            information.information_field
            for information in state.get("extracted_information", [])
        }
        required_fields = set(
            IntentInformationMapper.determine_fields(intent=expected.intent)
        )
        if changed_fields & required_fields:
            return {
                "expected_interaction": None,
                "current_intent": expected.intent,
                "last_intent_fulfilled": False,
                "confirmation_outcome": ConfirmationOutcome.CHANGED,
            }

        message = _required_message(state, "translated_message")
        decision = _confirmation_decision(message.content)
        if decision is True:
            return {
                "expected_interaction": None,
                "current_intent": expected.intent,
                "domain_operation": expected.operation,
                "confirmation_outcome": ConfirmationOutcome.CONFIRMED,
            }
        if decision is False:
            return {
                "expected_interaction": None,
                "last_intent_fulfilled": True,
                "action": Action.ASK_INTENT,
                "domain_data": None,
                "confirmation_outcome": ConfirmationOutcome.DECLINED,
            }

        detected_intent = state.get("detected_intent") or Intent.UNKNOWN
        if detected_intent not in {Intent.UNKNOWN, expected.intent}:
            return {
                "expected_interaction": None,
                "confirmation_outcome": ConfirmationOutcome.INTERRUPTED,
            }

        return {
            "action": Action.ASK_FOR_CONFIRMATION,
            "domain_data": dict(state.get("collected_information", {})),
            "confirmation_outcome": ConfirmationOutcome.UNCLEAR,
        }

    def activate_intent(self, state: ConversationState) -> StateUpdate:
        """Resolve whether to switch, resume, greet, or ask for an intent."""

        detected = state.get("detected_intent") or Intent.UNKNOWN
        current = state.get("current_intent", Intent.CONVERSATION_INITIATION)
        extracted_fields = {
            information.information_field
            for information in state.get("extracted_information", [])
        }

        if detected == Intent.CONVERSATION_INITIATION:
            return {
                "action": Action.DISPLAY_GREETING,
                "domain_data": None,
            }

        if detected != Intent.UNKNOWN:
            return {
                "current_intent": detected,
                "last_intent_fulfilled": False,
            }

        required_fields = set(IntentInformationMapper.determine_fields(intent=current))
        current_is_open = not state.get("last_intent_fulfilled", False)
        if current_is_open or bool(extracted_fields & required_fields):
            return {
                "current_intent": current,
                "last_intent_fulfilled": False,
            }

        return {
            "action": Action.ASK_INTENT,
            "domain_data": None,
        }

    def determine_missing_fields(self, state: ConversationState) -> StateUpdate:
        """Calculate required fields for the active intent from graph state."""

        current_intent = state.get(
            "current_intent",
            Intent.CONVERSATION_INITIATION,
        )
        required_fields = IntentInformationMapper.determine_fields(
            intent=current_intent,
        )
        information = state.get("collected_information", {})
        missing_fields = [
            field
            for field in required_fields
            if field not in information or not information[field].is_valid()
        ]
        return {"missing_fields": missing_fields}

    def determine_action(self, state: ConversationState) -> StateUpdate:
        """Select a response action or domain operation deterministically."""

        current_intent = state.get(
            "current_intent",
            Intent.CONVERSATION_INITIATION,
        )
        missing_fields = state.get("missing_fields", [])
        if missing_fields:
            return {
                "action": Action.ASK_FOR_DATA,
                "domain_data": list(missing_fields),
                "last_intent_fulfilled": False,
            }

        operation_by_intent = {
            Intent.AVAILABILITY_CHECK: DomainOperation.FIND_AVAILABILITY,
            Intent.BOOKING_CHECK: DomainOperation.GET_BOOKING,
            Intent.INFORMATION_REQUEST: DomainOperation.GET_INFORMATION,
            Intent.BOOKING_CANCELLATION: DomainOperation.GET_BOOKING,
        }
        operation = operation_by_intent.get(current_intent)
        if operation is not None:
            return {"domain_operation": operation}

        if current_intent == Intent.BOOKING_REQUEST:
            expected = ExpectedInteraction(
                kind=ExpectedInteractionKind.BOOKING_CONFIRMATION,
                intent=current_intent,
                operation=DomainOperation.CREATE_BOOKING,
            )
            return {
                "action": Action.ASK_FOR_CONFIRMATION,
                "domain_data": dict(state.get("collected_information", {})),
                "expected_interaction": expected,
                "last_intent_fulfilled": False,
            }
        """
        if current_intent == Intent.BOOKING_CANCELLATION:
            expected = ExpectedInteraction(
                kind=ExpectedInteractionKind.CANCELLATION_CONFIRMATION,
                intent=current_intent,
                operation=DomainOperation.CANCEL_BOOKING,
            )
            return {
                "action": Action.ASK_FOR_CONFIRMATION,
                "domain_data": dict(state.get("collected_information", {})),
                "expected_interaction": expected,
                "last_intent_fulfilled": False,
            }
        """

        return {"action": Action.ASK_INTENT, "domain_data": None}

    def execute_domain_action(self, state: ConversationState) -> StateUpdate:
        """Delegate a selected operation and retain only its result in state."""

        operation = state.get("domain_operation")
        if operation is None:
            raise ValueError("No domain operation was selected")

        try:
            result = self.domain_adapter.execute(
                operation=operation,
                information=state.get("collected_information", {}),
            )
        except (KeyError, RuntimeError, TypeError, ValueError) as error:
            response = self.user_interaction.send_error_msg(reason=str(error))
            return {
                "domain_operation": None,
                "response": response,
                "response_in_domain_language": response.text,
                "session_active": response.session_active,
                "last_intent_fulfilled": False,
            }
        
        if (
            operation == DomainOperation.GET_BOOKING
            and state.get("current_intent") == Intent.BOOKING_CANCELLATION
        ):
            if result is None:
                return {
                    "domain_operation": None,
                    "domain_data": None,
                    "action": Action.DISPLAY_BOOKING,
                    "last_intent_fulfilled": False,
                }

            if isinstance(result, Booking) and result.status == BookingStatus.CANCELLED:
                return {
                    "domain_operation": None,
                    "domain_data": result,
                    "action": Action.DISPLAY_BOOKING,
                    "expected_interaction": None,
                    "last_intent_fulfilled": True,
                }

            expected = ExpectedInteraction(
                kind=ExpectedInteractionKind.CANCELLATION_CONFIRMATION,
                intent=Intent.BOOKING_CANCELLATION,
                operation=DomainOperation.CANCEL_BOOKING,
            )
            return {
                "domain_operation": None,
                "domain_data": result,
                "action": Action.ASK_FOR_CONFIRMATION,
                "expected_interaction": expected,
                "last_intent_fulfilled": False,
            }

        response_action = {
            DomainOperation.FIND_AVAILABILITY: Action.DISPLAY_AVAILABILITY,
            DomainOperation.GET_BOOKING: Action.DISPLAY_BOOKING,
            DomainOperation.CREATE_BOOKING: Action.DISPLAY_BOOKING,
            DomainOperation.CANCEL_BOOKING: Action.DISPLAY_BOOKING,
            DomainOperation.GET_INFORMATION: Action.DISPLAY_INFO,
        }[operation]
        return {
            "domain_operation": None,
            "domain_data": result,
            "action": response_action,
            "last_intent_fulfilled": True,
        }

    def build_response(self, state: ConversationState) -> StateUpdate:
        """Build an ``InteractionResponse`` through the existing UI component."""

        existing_response = state.get("response")
        if existing_response is not None:
            return {}

        action = state.get("action")
        if action is None:
            raise ValueError("Response construction requires an action")

        response = self.user_interaction.build_response(
            action=action,
            intent=state.get(
                "current_intent",
                Intent.CONVERSATION_INITIATION,
            ),
            data=state.get("domain_data"),
        )
        return {
            "response": response,
            "response_in_domain_language": response.text,
            "session_active": response.session_active,
        }

    def terminate_conversation(self, state: ConversationState) -> StateUpdate:
        """Return the final error response after too many unknown turns."""

        response = self.user_interaction.send_error_msg(
            reason="Unknown intent threshold exceeded",
        )
        return {
            "response": response,
            "response_in_domain_language": response.text,
            "session_active": False,
            "expected_interaction": None,
        }

    def translate_response(self, state: ConversationState) -> StateUpdate:
        """Translate a response copy into the session language."""

        response = state.get("response")
        if response is None or not response.text:
            return {}

        session_language = state.get("language") or self.domain_language
        if session_language == self.domain_language:
            return {}

        translated = self.translator.translate(
            Message(content=response.text),
            target_lang=session_language,
        )
        return {"response": replace(response, text=translated.content)}

    def store_assistant_message(self, state: ConversationState) -> StateUpdate:
        """Append the assistant's domain-language and displayed text to history."""

        response = state.get("response")
        if response is None or not response.text:
            return {}

        domain_text = state.get("response_in_domain_language") or response.text
        session_language = state.get("language") or self.domain_language
        message = Message(
            content=domain_text,
            original_content=response.text,
            language=session_language,
        )
        return {
            "message_history": [
                ConversationMessage(
                    role=MessageRole.ASSISTANT,
                    message=message,
                )
            ]
        }

    def write_state_to_logs(
            self,
            state: ConversationState,
        ) -> StateUpdate:
            """Write conversation state to logs after processing a message."""
            serialized_state = to_jsonable(state)

            LOG_MSG.debug(
                "Conversation message processed",
                extra={
                    "conversation_state": serialized_state,
                },
            )

            return {
                "initialized": state["initialized"],
            }
    
def _required_message(
    state: ConversationState,
    key: Literal["parsed_message", "translated_message"],
) -> Message:
    value = state.get(key)
    if not isinstance(value, Message):
        raise TypeError(f"State field {key} must contain a Message")
    return value


def _contextual_model_message(
    state: ConversationState,
    domain_language: str,
) -> Message:
    current = _required_message(state, "translated_message")
    history_lines = [
        f"{entry.role.value.title()}: {entry.message.content}"
        for entry in state.get("message_history", [])
        if entry.message_id != current.message_id
    ]
    history = "\n".join(history_lines) or "(no previous messages)"
    content = (
        f"Conversation history:\n{history}\n\nCurrent user message:\n{current.content}"
    )
    return replace(current, content=content, language=domain_language)


def _confirmation_decision(content: str) -> bool | None:
    normalized = " ".join(content.casefold().strip().split()).strip(".,!?")
    affirmative = {"yes", "yes please", "confirm", "confirmed", "proceed"}
    negative = {"no", "no thanks", "cancel", "decline", "stop"}
    if normalized in affirmative:
        return True
    if normalized in negative:
        return False
    return None


def _booking_request_tuple_from_information(
    information: Mapping[InformationField, Information],
) -> tuple[date, date, int, bool, bool | None]:
    check_in = _required_date(information, InformationField.CHECK_IN)
    check_out = _required_date(information, InformationField.CHECK_OUT)
    guest_count = _required_int(information, InformationField.GUEST_COUNT)
    accessible = _required_bool(information, InformationField.ACCESSIBLE)
    breakfast = _optional_bool(
        information,
        InformationField.BREAKFAST,
        default=False,
    )
    return (check_in, check_out, guest_count, accessible, breakfast)

def _create_customer_from_information(
        information: Mapping[InformationField, Information],
        database: DatabaseInterface
) -> Customer:
    first_name = _required_string(information, InformationField.FIRST_NAME)
    last_name = _required_string(information, InformationField.LAST_NAME)
    email = _required_string(information, InformationField.EMAIL)
    preferred_language = _required_string(information, InformationField.PREFERRED_LANG)
    phone = _optional_string(
        information,
        InformationField.PHONE,
        default="0",
    )
    customer = create_customer(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        preferred_language=preferred_language,
        database=database
    )
    if not isinstance(customer, Customer):
        raise TypeError("error in _create_customer_from_information")
    return customer


def _required_content(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> str | bool | int | date:
    try:
        return information[field].content
    except KeyError as error:
        raise KeyError(f"Missing required information: {field.value}") from error


def _required_string(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> str:
    value = _required_content(information, field)
    if not isinstance(value, str):
        raise TypeError(f"{field.value} must be a string")
    return value


def _required_bool(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> bool:
    value = _required_content(information, field)
    if not isinstance(value, bool):
        raise TypeError(f"{field.value} must be a boolean")
    return value


def _optional_bool(
    information: Mapping[InformationField, Information],
    field: InformationField,
    *,
    default: bool,
) -> bool:
    value = information.get(field)
    if value is None:
        return default
    if not isinstance(value.content, bool):
        raise TypeError(f"{field.value} must be a boolean")
    return value.content

def _optional_string(
    information: Mapping[InformationField, Information],
    field: InformationField,
    *,
    default: str,
) -> str:
    value = information.get(field)
    if value is None:
        return default
    if not isinstance(value.content, str):
        raise TypeError(f"{field.value} must be a string")
    return value.content


def _required_int(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> int:
    value = _required_content(information, field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field.value} must be an integer")
    return value


def _required_date(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> date:
    value = _required_content(information, field)
    if not isinstance(value, date):
        raise TypeError(f"{field.value} must be a date")
    return value


def nodes_from_settings(
    *,
    translator: TranslatorInterface,
    intent_classifier: IntentClassifier,
    information_extractor: InformationExtractor,
    user_interaction: UserInteraction,
    domain_adapter: ConversationDomainAdapter,
) -> ConversationNodes:
    """Create graph nodes from the existing application settings."""

    settings = ApplicationSettings.get_settings()
    return ConversationNodes(
        translator=translator,
        intent_classifier=intent_classifier,
        information_extractor=information_extractor,
        user_interaction=user_interaction,
        domain_adapter=domain_adapter,
        domain_language=settings.domain_language,
        max_unknown_messages=settings.max_num_msg_with_intent_unknown,
    )
