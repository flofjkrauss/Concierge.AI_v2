"""Tests for best-effort conversation state logging."""

from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

from conversation.graph.nodes import write_state_to_logs as module
from conversation.graph.nodes.context import ConversationNodeContext
from conversation.graph.state import ConversationState


def test_logging_failure_does_not_break_conversation(monkeypatch) -> None:
    debug = Mock(side_effect=TypeError("not serializable"))
    monkeypatch.setattr(module.LOG_MSG, "debug", debug)

    result = module.write_state_to_logs(
        cast(ConversationNodeContext, SimpleNamespace()),
        cast(ConversationState, {"initialized": True}),
    )

    assert result == {"initialized": True}
