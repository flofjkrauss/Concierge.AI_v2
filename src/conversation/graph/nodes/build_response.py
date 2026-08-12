"""Implementation of the build_response conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    ConversationState,
    Intent,
    StateUpdate,
    _is_valid_interaction_response,
    _safe_error_response,
    _safe_log_exception,
)


def build_response(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Build an ``InteractionResponse`` through the existing UI component."""

    existing_response = state.get("response")

    if existing_response is not None:
        return {}

    action = state.get("action")

    if action is None:
        response = _safe_error_response(
            context.user_interaction,
            reason="Response construction requires an action",
        )
    else:
        try:
            response = context.user_interaction.build_response(
                action=action,
                intent=state.get(
                    "current_intent",
                    Intent.CONVERSATION_INITIATION,
                ),
                data=state.get("domain_data"),
            )
            if not _is_valid_interaction_response(response):
                raise TypeError("User interaction returned an invalid response")
        except Exception as error:  # noqa: BLE001
            _safe_log_exception("Response construction failed", error)
            response = _safe_error_response(
                context.user_interaction,
                reason="Response construction failed",
            )

    return {
        "response": response,
        "response_in_domain_language": response.text,
        "session_active": response.session_active,
    }


__all__ = ["build_response"]
