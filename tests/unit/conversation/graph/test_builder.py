from __future__ import annotations

from conftest import InMemoryDatabase
from langgraph.checkpoint.memory import InMemorySaver

from conversation.entities.interaction_response import GreetingResponse
from conversation.entities.message import Message
from conversation.graph.builder import (
    CHECKPOINT_TYPE_ALLOWLIST,
    build_conversation_graph,
    create_in_memory_checkpointer,
)
from conversation.models.information.interface import InformationExtractorInterface
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.models.translation.interface import NoneTranslator
from conversation.user_interaction import UserInteraction
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


class GreetingClassifier(IntentionDetectorInterface):
    def determine(self, message: Message) -> Intent:
        return Intent.CONVERSATION_INITIATION


class EmptyExtractor(InformationExtractorInterface):
    def extract(
        self,
        message: Message,
        expected_field: InformationField | None = None,
    ) -> list:
        return []


class GreetingInteraction(UserInteraction):
    def display_greeting(self, intent: Intent, data: object) -> GreetingResponse:
        return GreetingResponse(
            session_active=True,
            text="Welcome! How can I help you?",
            session_id=str(data),
        )


def build_graph(database: InMemoryDatabase):
    return build_conversation_graph(
        database=database,
        translator=NoneTranslator(),
        intent_classifier=GreetingClassifier(),
        information_extractor=EmptyExtractor(),
        user_interaction=GreetingInteraction(),
        checkpointer=create_in_memory_checkpointer(),
    )


def test_create_in_memory_checkpointer_uses_explicit_serializer_policy() -> None:
    checkpointer = create_in_memory_checkpointer()

    assert isinstance(checkpointer, InMemorySaver)
    assert ("conversation.entities.message", "Message") in CHECKPOINT_TYPE_ALLOWLIST
    assert ("conversation.graph.state", "ConversationMessage") in (
        CHECKPOINT_TYPE_ALLOWLIST
    )


def test_compiled_graph_initializes_thread_and_persists_state(
    database: InMemoryDatabase,
) -> None:
    graph = build_graph(database)
    config = {"configurable": {"thread_id": "session-1"}}

    result = graph.invoke(
        {
            "session_id": "session-1",
            "session_active": True,
            "language": None,
            "incoming_message": None,
        },
        config,
    )

    assert result["session_active"] is True
    assert result["response"] is not None
    assert result["response"].session_id == "session-1"
    state = graph.get_state(config).values
    assert state["initialized"] is True
    assert state["session_id"] == "session-1"


def test_compiled_graph_processes_greeting_and_records_both_sides(
    database: InMemoryDatabase,
) -> None:
    graph = build_graph(database)
    config = {"configurable": {"thread_id": "session-1"}}
    graph.invoke(
        {
            "session_id": "session-1",
            "session_active": True,
            "language": None,
            "incoming_message": None,
        },
        config,
    )

    result = graph.invoke({"incoming_message": "Hello"}, config)

    assert isinstance(result["response"], GreetingResponse)
    history = graph.get_state(config).values["message_history"]
    assert [entry.role.value for entry in history] == ["user", "assistant"]
    assert history[0].message.content.endswith("Hello")
    assert history[1].message.content == "Welcome! How can I help you?"


def test_compiled_graph_keeps_thread_state_isolated(
    database: InMemoryDatabase,
) -> None:
    graph = build_graph(database)
    first = {"configurable": {"thread_id": "first"}}
    second = {"configurable": {"thread_id": "second"}}

    for session_id, config in (("first", first), ("second", second)):
        graph.invoke(
            {
                "session_id": session_id,
                "session_active": True,
                "language": None,
                "incoming_message": None,
            },
            config,
        )
    graph.invoke({"incoming_message": "Hello"}, first)

    assert len(graph.get_state(first).values["message_history"]) == 2
    assert graph.get_state(second).values["message_history"] == []
