from __future__ import annotations

from types import SimpleNamespace

from conversation.conversation_controller import ConversationController
from conversation.entities.interaction_response import (
    ErrorResponse,
    InteractionResponse,
)
from conversation.graph.state import ConversationInput, ConversationOutput
from conversation.user_interaction import UserInteraction


class FakeGraph:
    def __init__(self, result: ConversationOutput, state_values: dict[str, object]) -> None:
        self.result = result
        self.state_values = state_values
        self.invocations: list[tuple[ConversationInput, dict[str, object]]] = []
        self.updates: list[tuple[dict[str, object], dict[str, object]]] = []

    def invoke(
        self,
        input: ConversationInput,
        config: dict[str, object],
    ) -> ConversationOutput:
        self.invocations.append((input, config))
        return self.result

    def get_state(self, config: dict[str, object]) -> object:
        return SimpleNamespace(values=self.state_values)

    def update_state(
        self,
        config: dict[str, object],
        values: dict[str, object],
    ) -> object:
        self.updates.append((config, values))
        self.state_values.update(values)
        return config


def test_init_conversation_uses_same_session_id_for_input_and_thread() -> None:
    response = InteractionResponse(True, "session")
    graph = FakeGraph({"response": response, "session_active": True}, {})
    controller = ConversationController(graph, UserInteraction())

    assert controller.init_conversation() is response
    graph_input, config = graph.invocations[0]
    assert graph_input["session_id"]
    assert config == {
        "configurable": {"thread_id": graph_input["session_id"]}
    }


def test_process_message_rejects_unknown_session() -> None:
    graph = FakeGraph({"response": None, "session_active": False}, {})
    controller = ConversationController(graph, UserInteraction())

    response = controller.process_message("missing", "Hello")

    assert isinstance(response, ErrorResponse)
    assert response.reason == "Session not found"
    assert graph.invocations == []


def test_process_message_rejects_inactive_session() -> None:
    graph = FakeGraph(
        {"response": None, "session_active": False},
        {"session_active": False},
    )
    controller = ConversationController(graph, UserInteraction())

    response = controller.process_message("session-1", "Hello")

    assert isinstance(response, ErrorResponse)
    assert response.reason == "Session is not active"


def test_process_message_invokes_active_thread() -> None:
    expected = InteractionResponse(True, "Processed")
    graph = FakeGraph(
        {"response": expected, "session_active": True},
        {"session_active": True},
    )
    controller = ConversationController(graph, UserInteraction())

    assert controller.process_message("session-1", "Hello") is expected
    assert graph.invocations == [
        (
            {"incoming_message": "Hello"},
            {"configurable": {"thread_id": "session-1"}},
        )
    ]


def test_controller_returns_error_when_graph_has_no_response() -> None:
    graph = FakeGraph(
        {"response": None, "session_active": True},
        {"session_active": True},
    )
    controller = ConversationController(graph, UserInteraction())

    response = controller.process_message("session-1", "Hello")

    assert isinstance(response, ErrorResponse)
    assert response.reason == "Conversation graph returned no response"


def test_terminate_conversation_marks_known_session_inactive() -> None:
    graph = FakeGraph(
        {"response": None, "session_active": True},
        {"session_active": True, "expected_interaction": object()},
    )
    controller = ConversationController(graph, UserInteraction())

    controller.terminate_conversation("session-1")

    assert graph.updates == [
        (
            {"configurable": {"thread_id": "session-1"}},
            {"session_active": False, "expected_interaction": None},
        )
    ]


def test_terminate_conversation_ignores_unknown_session() -> None:
    graph = FakeGraph(
        {"response": None, "session_active": False},
        {},
    )
    controller = ConversationController(graph, UserInteraction())

    controller.terminate_conversation("missing")

    assert graph.updates == []
