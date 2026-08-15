"""Tests for the graph package's lazy public API."""

import pytest

import conversation.graph as graph_package
from conversation.graph import builder
from conversation.graph.state import ConversationState


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("ConversationState", ConversationState),
        ("ConversationGraph", builder.ConversationGraph),
        ("build_conversation_graph", builder.build_conversation_graph),
        ("create_in_memory_checkpointer", builder.create_in_memory_checkpointer),
    ],
)
def test_graph_package_lazily_exposes_public_objects(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    expected: object,
) -> None:
    monkeypatch.delitem(graph_package.__dict__, name, raising=False)

    assert getattr(graph_package, name) is expected
    assert graph_package.__dict__[name] is expected


def test_graph_package_rejects_unknown_attribute() -> None:
    with pytest.raises(AttributeError, match="unknown_graph_member"):
        graph_package.__getattr__("unknown_graph_member")
