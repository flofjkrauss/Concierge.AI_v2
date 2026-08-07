from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from uuid import UUID

from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.graph.state import ConversationMessage, MessageRole
from conversation.value_object.information_fields import InformationField
from domain.value_objects.booking_status import BookingStatus
from observability.utils.to_json import to_jsonable


def test_to_jsonable_handles_scalar_and_standard_types(tmp_path: Path) -> None:
    class ExampleEnum(Enum):
        VALUE = "value"

    assert to_jsonable(None) is None
    assert to_jsonable("text") == "text"
    assert to_jsonable(BookingStatus.CONFIRMED) == "confirmed"
    assert to_jsonable(ExampleEnum.VALUE) == "value"
    assert to_jsonable(date(2030, 1, 2)) == "2030-01-02"
    assert to_jsonable(datetime(2030, 1, 1, tzinfo=UTC)) == (
        "2030-01-01T00:00:00+00:00"
    )
    assert to_jsonable(UUID("12345678-1234-5678-1234-567812345678")) == (
        "12345678-1234-5678-1234-567812345678"
    )
    assert to_jsonable(tmp_path) == str(tmp_path)


def test_to_jsonable_serializes_messages_and_information() -> None:
    message = Message(
        "Hello",
        original_content="Hallo",
        language="de",
        message_id="message-1",
        created_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    information = Information(
        InformationField.FIRST_NAME,
        "Alex",
        information_id="information-1",
        created_at=datetime(2030, 1, 2, tzinfo=UTC),
    )

    assert to_jsonable(message)["original_content"] == "Hallo"
    assert to_jsonable([information]) == {
        "first_name": {
            "content": "Alex",
            "created_at": "2030-01-02T00:00:00+00:00",
            "information_id": "information-1",
        }
    }


def test_to_jsonable_serializes_conversation_history_by_index() -> None:
    entry = ConversationMessage(
        MessageRole.USER,
        Message("Hello", message_id="message-1"),
    )

    assert to_jsonable([entry]) == {
        "0": {
            "role": "user",
            "message": to_jsonable(entry.message),
        }
    }


def test_to_jsonable_recurses_through_mappings_and_collections() -> None:
    value = {
        BookingStatus.CONFIRMED: (
            InformationField.FIRST_NAME,
            {1, 2},
        )
    }

    result = to_jsonable(value)

    assert result.keys() == {"confirmed"}
    assert result["confirmed"][0] == "first_name"
    assert set(result["confirmed"][1]) == {1, 2}


def test_to_jsonable_serializes_generic_dataclass_and_fallback() -> None:
    @dataclass
    class Example:
        name: str

    class Unknown:
        def __repr__(self) -> str:
            return "Unknown()"

    assert to_jsonable(Example("value")) == {"name": "value"}
    assert to_jsonable(Unknown()) == "Unknown()"
