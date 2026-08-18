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

    if isinstance(value, list):
        contains_only_information = True
        for item in value:
            if not isinstance(item, Information):
                contains_only_information = False
                break

        # Information lists use their semantic field names as JSON keys.
        if contains_only_information:
            information_by_field: dict[str, Any] = {}
            for item in value:
                information_by_field[item.information_field.value] = to_jsonable(item)
            return information_by_field

        contains_only_messages = True
        for item in value:
            if not isinstance(item, ConversationMessage):
                contains_only_messages = False
                break

        # Message lists retain their order through stable numeric keys.
        if contains_only_messages:
            messages_by_index: dict[str, Any] = {}
            for index, item in enumerate(value):
                messages_by_index[str(index)] = to_jsonable(item)
            return messages_by_index

    if isinstance(value, Mapping):
        json_mapping: dict[str, Any] = {}
        for key, item in value.items():
            json_key = str(to_jsonable(key))
            json_mapping[json_key] = to_jsonable(item)
        return json_mapping

    if isinstance(value, list | tuple | set | frozenset):
        json_items: list[Any] = []
        for item in value:
            json_items.append(to_jsonable(item))
        return json_items

    if is_dataclass(value) and not isinstance(value, type):
        json_fields: dict[str, Any] = {}
        for field in fields(value):
            field_value = getattr(value, field.name)
            json_fields[field.name] = to_jsonable(field_value)
        return json_fields

    return repr(value)
