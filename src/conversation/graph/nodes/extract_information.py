"""Implementation of the extract_information conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    BookingSelection,
    ConversationState,
    StateUpdate,
    _booking_selection_information,
    _required_message,
    _safe_log_exception,
    _valid_extracted_information,
)


def extract_information(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Extract information on every turn, independently of intent."""

    message = _required_message(state, "translated_message")

    booking_selection = BookingSelection.from_wire(message.content)
    if booking_selection is not None:
        return {
            "extracted_information": _booking_selection_information(booking_selection)
        }

    try:
        extracted = context.information_extractor.extract(message=message)
        valid_information = _valid_extracted_information(extracted)
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Information extraction failed", error)
        valid_information = []

    return {"extracted_information": valid_information}


__all__ = ["extract_information"]
