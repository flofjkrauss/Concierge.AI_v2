"""LangGraph conversation orchestration."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conversation.graph.builder import (
        ConversationGraph,
        build_conversation_graph,
        create_in_memory_checkpointer,
    )
    from conversation.graph.state import ConversationState

__all__ = [
    "ConversationGraph",
    "ConversationState",
    "build_conversation_graph",
    "create_in_memory_checkpointer",
]


def __getattr__(name: str) -> object:
    """Load public graph objects lazily to avoid package import cycles."""

    if name == "ConversationState":
        from conversation.graph.state import ConversationState

        value: object = ConversationState
    elif name in {
        "ConversationGraph",
        "build_conversation_graph",
        "create_in_memory_checkpointer",
    }:
        from conversation.graph import builder

        value = getattr(builder, name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    globals()[name] = value
    return value
