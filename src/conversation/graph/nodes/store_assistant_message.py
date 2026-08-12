"""Implementation of the store_assistant_message conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    ConversationMessage,
    ConversationState,
    InteractionResponse,
    Message,
    MessageRole,
    StateUpdate,
)


def store_assistant_message(
    context: ConversationNodeContext,
    state: ConversationState,
) -> StateUpdate:
    """Append the assistant's domain-language and displayed text to history."""

    response = state.get("response")

    if (
        not isinstance(response, InteractionResponse)
        or not isinstance(response.text, str)
        or not response.text
    ):
        return {}

    domain_text = state.get("response_in_domain_language")
    if not isinstance(domain_text, str) or not domain_text:
        domain_text = response.text

    session_language = state.get("language") or context.domain_language

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


__all__ = ["store_assistant_message"]
