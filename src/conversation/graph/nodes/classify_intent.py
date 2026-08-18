"""Implementation of the classify_intent conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    BookingSelection,
    ConversationState,
    InformationTopicSelection,
    Intent,
    StateUpdate,
    _required_message,
    _safe_log_exception,
    _safe_log_warning,
)


def classify_intent(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Classify intent using the current message plus both-sided history."""

    message = _required_message(state, "translated_message")

    if InformationTopicSelection.from_wire(message.content) is not None:
        detected = Intent.INFORMATION_REQUEST
    elif BookingSelection.from_wire(message.content) is not None:
        detected = Intent.BOOKING_REQUEST
    else:
        try:
            detected = context.intent_classifier.determine(message=message)
        except Exception as error:  # noqa: BLE001
            _safe_log_exception("Intent detection failed", error)
            detected = Intent.UNKNOWN

    if not isinstance(detected, Intent):
        try:
            detected = Intent(detected) if isinstance(detected, str) else Intent.UNKNOWN
        except ValueError:
            detected = Intent.UNKNOWN

        if detected == Intent.UNKNOWN:
            _safe_log_warning("Intent detector returned an invalid intent")

    if (
        detected == Intent.BOOKING_REQUEST
        and not state.get("availability_requested", False)
    ):
        detected = Intent.AVAILABILITY_CHECK

    return {"detected_intent": detected}


__all__ = ["classify_intent"]
