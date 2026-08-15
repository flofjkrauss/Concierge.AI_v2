"""Pure reducers for LangGraph conversation state fields."""

from collections.abc import Mapping, Sequence
from typing import Protocol

from conversation.entities.information import Information
from conversation.value_object.information_fields import InformationField


class IdentifiedMessage(Protocol):
    """Structural type for message-history entries."""

    @property
    def message_id(self) -> str:
        """Return the stable ID of the wrapped message."""


def merge_messages[MessageEntry: IdentifiedMessage](
    current: Sequence[MessageEntry] | None,
    updates: Sequence[MessageEntry] | None,
) -> list[MessageEntry]:
    """Append new messages and replace entries with an existing message ID."""

    merged = list(current or ())
    positions = {entry.message_id: index for index, entry in enumerate(merged)}

    for entry in updates or ():
        existing_index = positions.get(entry.message_id)
        if existing_index is None:
            positions[entry.message_id] = len(merged)
            merged.append(entry)
        else:
            merged[existing_index] = entry

    return merged


def merge_information(
    current: Mapping[InformationField, Information] | None,
    updates: Mapping[InformationField, Information | None] | None,
) -> dict[InformationField, Information]:
    """Merge or remove information without mutating either input mapping.

    A new value replaces the old value for the same ``InformationField``.
    ``None`` removes the field so request-scoped values can be cleaned up.
    """

    merged = dict(current or {})

    for field, information in (updates or {}).items():
        if information is None:
            merged.pop(field, None)
        else:
            merged[field] = information

    return merged
