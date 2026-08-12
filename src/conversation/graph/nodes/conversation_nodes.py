"""Application-scoped facade exposing all compiled graph node callables."""

from dataclasses import dataclass

from conversation.graph.state import ConversationState
from conversation.models.information.interface import InformationExtractorInterface
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.models.translation.interface import TranslatorInterface
from conversation.user_interaction import UserInteraction

from .activate_intent import activate_intent as _activate_intent
from .begin_turn import begin_turn as _begin_turn
from .build_response import build_response as _build_response
from .classify_intent import classify_intent as _classify_intent
from .determine_action import determine_action as _determine_action
from .determine_missing_fields import (
    determine_missing_fields as _determine_missing_fields,
)
from .domain_adapter import ConversationDomainAdapter
from .execute_domain_action import execute_domain_action as _execute_domain_action
from .extract_information import extract_information as _extract_information
from .resolve_confirmation import resolve_confirmation as _resolve_confirmation
from .store_assistant_message import store_assistant_message as _store_assistant_message
from .store_user_message import store_user_message as _store_user_message
from .support import StateUpdate
from .terminate_conversation import terminate_conversation as _terminate_conversation
from .translate_input import translate_input as _translate_input
from .translate_response import translate_response as _translate_response
from .update_progress import update_progress as _update_progress
from .write_state_to_logs import write_state_to_logs as _write_state_to_logs


@dataclass(frozen=True, slots=True)
class ConversationNodes:
    """Graph callables sharing application-scoped dependencies."""

    translator: TranslatorInterface
    intent_classifier: IntentionDetectorInterface
    information_extractor: InformationExtractorInterface
    user_interaction: UserInteraction
    domain_adapter: ConversationDomainAdapter
    domain_language: str
    max_unknown_messages: int

    def begin_turn(self, state: ConversationState) -> StateUpdate:
        return _begin_turn(self, state)

    def translate_input(self, state: ConversationState) -> StateUpdate:
        return _translate_input(self, state)

    def store_user_message(self, state: ConversationState) -> StateUpdate:
        return _store_user_message(self, state)

    def classify_intent(self, state: ConversationState) -> StateUpdate:
        return _classify_intent(self, state)

    def extract_information(self, state: ConversationState) -> StateUpdate:
        return _extract_information(self, state)

    def update_progress(self, state: ConversationState) -> StateUpdate:
        return _update_progress(self, state)

    def resolve_confirmation(self, state: ConversationState) -> StateUpdate:
        return _resolve_confirmation(self, state)

    def activate_intent(self, state: ConversationState) -> StateUpdate:
        return _activate_intent(self, state)

    def determine_missing_fields(self, state: ConversationState) -> StateUpdate:
        return _determine_missing_fields(self, state)

    def determine_action(self, state: ConversationState) -> StateUpdate:
        return _determine_action(self, state)

    def execute_domain_action(self, state: ConversationState) -> StateUpdate:
        return _execute_domain_action(self, state)

    def build_response(self, state: ConversationState) -> StateUpdate:
        return _build_response(self, state)

    def terminate_conversation(self, state: ConversationState) -> StateUpdate:
        return _terminate_conversation(self, state)

    def translate_response(self, state: ConversationState) -> StateUpdate:
        return _translate_response(self, state)

    def store_assistant_message(self, state: ConversationState) -> StateUpdate:
        return _store_assistant_message(self, state)

    def write_state_to_logs(self, state: ConversationState) -> StateUpdate:
        return _write_state_to_logs(self, state)


__all__ = ["ConversationNodes"]
