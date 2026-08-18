"""Implementation of the determine_missing_fields conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    ConversationState,
    Intent,
    IntentInformationMapper,
    StateUpdate,
    _is_valid_information,
)


def determine_missing_fields(
    context: ConversationNodeContext,
    state: ConversationState,
) -> StateUpdate:
    """Calculate required fields for the active intent from graph state."""

    current_intent = state.get(
        "current_intent",
        Intent.CONVERSATION_INITIATION,
    )

    required_fields = IntentInformationMapper.determine_required_fields(
        intent=current_intent,
    )

    information = state.get("collected_information", {})

    missing_fields = []
    for field in required_fields:
        if field not in information or not _is_valid_information(information[field]):
            missing_fields.append(field)

    next_missing_field = None

    if missing_fields:
        next_missing_field = missing_fields[0]

    return {
        "missing_fields": missing_fields,
        "next_missing_field": next_missing_field,
    }


__all__ = ["determine_missing_fields"]
