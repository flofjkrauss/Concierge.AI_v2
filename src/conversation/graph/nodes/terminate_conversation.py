"""Implementation of the terminate_conversation conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    ConversationState,
    StateUpdate,
    _safe_error_response,
)


def terminate_conversation(
    context: ConversationNodeContext,
    state: ConversationState,
) -> StateUpdate:
    """Return the final error response after too many unknown turns."""

    response = _safe_error_response(
        context.user_interaction,
        reason="Unknown intent threshold exceeded",
        session_active=False,
    )

    return {
        "response": response,
        "response_in_domain_language": response.text,
        "session_active": False,
        "expected_interaction": None,
        "pending_information_changes": {},
    }


__all__ = ["terminate_conversation"]
