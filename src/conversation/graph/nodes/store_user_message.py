"""Implementation of the store_user_message conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    ConversationMessage,
    ConversationState,
    MessageRole,
    StateUpdate,
    _required_message,
)


def store_user_message(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Append the normalized user message to authoritative history."""

    message = _required_message(state, "translated_message")

    return {
        "message_history": [
            ConversationMessage(
                role=MessageRole.USER,
                message=message,
            )
        ]
    }


__all__ = ["store_user_message"]
