from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.graph.state import ConversationMessage


def to_jsonable(value: Any) -> Any:
    """Recursively convert application objects into JSON-compatible values."""

    if value is None or isinstance(value, str | int | float | bool):
        return value

    if isinstance(value, Enum):
        return to_jsonable(value.value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, UUID | Path):
        return str(value)

    if isinstance(value, ConversationMessage):
        return {
            "role": value.role.value,
            "message": to_jsonable(value.message),
        }

    if isinstance(value, Message):
        return {
            "content": to_jsonable(value.content),
            "original_content": to_jsonable(value.original_content),
            "language": value.language,
            "message_id": to_jsonable(value.message_id),
            "created_at": to_jsonable(value.created_at),
        }

    if isinstance(value, Information):
        # Do not repeat information_field here.
        # The surrounding dictionary or Information-list serializer supplies it.
        return {
            "content": to_jsonable(value.content),
            "created_at": to_jsonable(value.created_at),
            "information_id": to_jsonable(value.information_id),
        }

    # Convert a list of Information entities into a field-indexed dictionary.
    if isinstance(value, list) and all(
        isinstance(item, Information) for item in value
    ):
        return {
            item.information_field.value: to_jsonable(item)
            for item in value
        }

    # Convert a list of conversation messages into a field-indexed dictionary.
    if isinstance(value, list) and all(
        isinstance(item, ConversationMessage) for item in value
    ):
        return {
            f"{index}": to_jsonable(item)
            for index, item in enumerate(value)
        }

    if isinstance(value, Mapping):
        return {
            str(to_jsonable(key)): to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, list | tuple | set | frozenset):
        return [
            to_jsonable(item)
            for item in value
        ]

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }

    return repr(value)