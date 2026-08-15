"""Implementation of the write_state_to_logs conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    LOG_MSG,
    ConversationState,
    StateUpdate,
    to_jsonable,
)


def write_state_to_logs(
    context: ConversationNodeContext,
    state: ConversationState,
) -> StateUpdate:
    """Write conversation state to logs after processing a message."""

    try:
        LOG_MSG.debug(
            "Conversation message processed",
            extra=to_jsonable(state),
        )
    except Exception:  # noqa: BLE001, S110
        pass

    return {
        "initialized": state.get("initialized", False),
    }


__all__ = ["write_state_to_logs"]
