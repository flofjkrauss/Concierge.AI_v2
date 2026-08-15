"""Focused branch tests for the begin-turn graph node."""

from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

from conversation.entities.interaction_response import ErrorResponse
from conversation.graph.nodes.begin_turn import begin_turn
from conversation.graph.nodes.context import ConversationNodeContext
from conversation.graph.state import ConversationState
from conversation.user_interaction import UserInteraction


def _context(interaction: Mock) -> ConversationNodeContext:
    return cast(
        ConversationNodeContext,
        SimpleNamespace(user_interaction=interaction),
    )


def _state(**values: object) -> ConversationState:
    return cast(ConversationState, values)


def _error_response(*, reason: str, session_active: bool = True) -> ErrorResponse:
    return ErrorResponse(session_active, "Error", reason)


def test_begin_turn_rejects_non_string_input_without_raising() -> None:
    interaction = Mock(spec=UserInteraction)
    interaction.send_error_msg.side_effect = _error_response

    result = begin_turn(
        _context(interaction),
        _state(initialized=True, incoming_message=123),
    )

    assert isinstance(result["response"], ErrorResponse)
    assert result["response"].reason == "Invalid message type"


def test_begin_turn_converts_parser_exception_to_safe_error() -> None:
    interaction = Mock(spec=UserInteraction)
    interaction.parse_message.side_effect = RuntimeError("parser failed")
    interaction.send_error_msg.side_effect = _error_response

    result = begin_turn(
        _context(interaction),
        _state(initialized=True, incoming_message="Hello"),
    )

    assert isinstance(result["response"], ErrorResponse)
    assert result["response"].reason == "Invalid message"


def test_begin_turn_replaces_invalid_empty_response_with_safe_error() -> None:
    interaction = Mock(spec=UserInteraction)
    interaction.send_empty_response.return_value = object()
    interaction.send_error_msg.side_effect = _error_response

    result = begin_turn(
        _context(interaction),
        _state(initialized=True, incoming_message=""),
    )

    assert isinstance(result["response"], ErrorResponse)
    assert result["response"].reason == "Empty response construction failed"
