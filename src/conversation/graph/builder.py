"""Build and compile the authoritative LangGraph conversation workflow."""

from typing import Protocol, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from conversation.graph.nodes import (
    ConversationDomainAdapter,
    DatabaseDomainAdapter,
    nodes_from_settings,
)
from conversation.graph.routing import (
    route_after_action,
    route_after_analysis,
    route_after_begin,
    route_after_confirmation,
    route_after_intent,
)
from conversation.graph.state import (
    ConversationInput,
    ConversationOutput,
    ConversationState,
)
from conversation.models.information.interface import InformationExtractorInterface
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.models.translation.interface import TranslatorInterface
from conversation.user_interaction import UserInteraction
from database.interface import DatabaseInterface


class ConversationGraph(Protocol):
    """Typing-only interface implemented by the compiled ``StateGraph``."""

    def invoke(
        self,
        input: ConversationInput,
        config: dict[str, object],
    ) -> ConversationOutput:
        """Run one graph invocation."""

        ...

    def get_state(self, config: dict[str, object]) -> object:
        """Return the current checkpoint snapshot."""

        ...

    def update_state(
        self,
        config: dict[str, object],
        values: dict[str, object],
    ) -> object:
        """Apply a focused update to one checkpointed conversation."""

        ...


CHECKPOINT_TYPE_ALLOWLIST: tuple[tuple[str, str], ...] = (
    ("api.schemas.availability_schema", "AvailabilityResponse"),
    ("api.schemas.availability_schema", "RoomResponse"),
    ("api.schemas.booking_schema", "BookingResponse"),
    ("conversation.entities.information", "Information"),
    ("conversation.entities.interaction_response", "AvailabilityResponse"),
    ("conversation.entities.interaction_response", "BookingResponse"),
    ("conversation.entities.interaction_response", "EmptyInteractionResponse"),
    ("conversation.entities.interaction_response", "ErrorResponse"),
    ("conversation.entities.interaction_response", "GreetingResponse"),
    ("conversation.entities.interaction_response", "InformationResponse"),
    ("conversation.entities.interaction_response", "InteractionResponse"),
    ('conversation.entities.interaction_response', 'AskConfirmationResponse'),
    ("conversation.entities.message", "Message"),
    ("conversation.graph.state", "ConfirmationOutcome"),
    ("conversation.graph.state", "ConversationMessage"),
    ("conversation.graph.state", "DomainOperation"),
    ("conversation.graph.state", "ExpectedInteraction"),
    ("conversation.graph.state", "ExpectedInteractionKind"),
    ("conversation.graph.state", "MessageRole"),
    ("conversation.value_object.action", "Action"),
    ("conversation.value_object.information_fields", "InformationField"),
    ("conversation.value_object.intent", "Intent"),
    ("domain.entities.booking", "Booking"),
    ("domain.entities.booking_request", "BookingRequest"),
    ("domain.entities.customer", "Customer"),
    ("domain.entities.room", "Room"),
    ("domain.value_objects.booking_status", "BookingStatus"),
    ("domain.value_objects.information_topic", "InformationTopic"),
    ("domain.value_objects.money", "Money"),
    ("domain.value_objects.room_category", "RoomCategory"),
    ("domain.value_objects.stay_period", "StayPeriod"),
    ("domain.services.find_matching_rooms", "MatchResponse"),
    ('conversation.value_object.default_phrases', 'DefaultPhrases'),
)


def create_in_memory_checkpointer() -> InMemorySaver:
    """Create the explicit, local-only serializer policy for conversation state."""

    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=CHECKPOINT_TYPE_ALLOWLIST,
    )
    return InMemorySaver(serde=serializer)


def build_conversation_graph(
    *,
    database: DatabaseInterface,
    translator: TranslatorInterface,
    intent_classifier: IntentionDetectorInterface,
    information_extractor: InformationExtractorInterface,
    user_interaction: UserInteraction,
    checkpointer: BaseCheckpointSaver[str],
    domain_adapter: ConversationDomainAdapter | None = None,
) -> ConversationGraph:
    """Compile the conversation graph with thread-level in-memory state.

    ``domain_adapter`` is primarily a test/customization seam. The default
    adapter calls the repository's existing domain services.
    """

    selected_domain_adapter = domain_adapter or DatabaseDomainAdapter(
        database=database
    )
    nodes = nodes_from_settings(
        translator=translator,
        intent_classifier=intent_classifier,
        information_extractor=information_extractor,
        user_interaction=user_interaction,
        domain_adapter=selected_domain_adapter,
    )

    workflow = StateGraph(
        ConversationState,
        input_schema=ConversationInput,
        output_schema=ConversationOutput,
    )
    workflow.add_node("begin_turn", nodes.begin_turn)
    workflow.add_node("translate_input", nodes.translate_input)
    workflow.add_node("store_user_message", nodes.store_user_message)
    workflow.add_node("classify_intent", nodes.classify_intent)
    workflow.add_node("extract_information", nodes.extract_information)
    workflow.add_node("update_progress", nodes.update_progress)
    workflow.add_node("resolve_confirmation", nodes.resolve_confirmation)
    workflow.add_node("activate_intent", nodes.activate_intent)
    workflow.add_node("determine_missing_fields", nodes.determine_missing_fields)
    workflow.add_node("determine_action", nodes.determine_action)
    workflow.add_node("execute_domain_action", nodes.execute_domain_action)
    workflow.add_node("build_response", nodes.build_response)
    workflow.add_node("terminate_conversation", nodes.terminate_conversation)
    workflow.add_node("translate_response", nodes.translate_response)
    workflow.add_node("store_assistant_message", nodes.store_assistant_message)
    workflow.add_node("write_state_to_logs", nodes.write_state_to_logs)

    workflow.add_edge(START, "begin_turn")
    workflow.add_conditional_edges(
        "begin_turn",
        route_after_begin,
        {"process": "translate_input", "finish": END},
    )
    workflow.add_edge("translate_input", "store_user_message")
    workflow.add_edge("store_user_message", "classify_intent")
    workflow.add_edge("classify_intent", "extract_information")
    workflow.add_edge("extract_information", "update_progress")
    workflow.add_conditional_edges(
        "update_progress",
        route_after_analysis,
        {
            "terminate": "terminate_conversation",
            "confirmation": "resolve_confirmation",
            "intent": "activate_intent",
        },
    )
    workflow.add_conditional_edges(
        "resolve_confirmation",
        route_after_confirmation,
        {
            "execute": "execute_domain_action",
            "fields": "determine_missing_fields",
            "intent": "activate_intent",
            "response": "build_response",
        },
    )
    workflow.add_conditional_edges(
        "activate_intent",
        route_after_intent,
        {"fields": "determine_missing_fields", "response": "build_response"},
    )
    workflow.add_edge("determine_missing_fields", "determine_action")
    workflow.add_conditional_edges(
        "determine_action",
        route_after_action,
        {"execute": "execute_domain_action", "response": "build_response"},
    )
    workflow.add_edge("execute_domain_action", "build_response")
    workflow.add_edge("build_response", "translate_response")
    workflow.add_edge("terminate_conversation", "translate_response")
    workflow.add_edge("translate_response", "store_assistant_message")
    workflow.add_edge("store_assistant_message", "write_state_to_logs")
    workflow.add_edge("write_state_to_logs", END)

    return cast(
        ConversationGraph,
        workflow.compile(checkpointer=checkpointer),
    )
