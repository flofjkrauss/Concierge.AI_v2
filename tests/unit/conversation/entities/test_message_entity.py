from datetime import UTC, datetime

import pytest

from conversation.entities.message import Message


def test_message_generates_identity_and_timezone_aware_timestamp() -> None:
    message = Message(content="Hello")

    assert message.message_id
    assert message.created_at.tzinfo is not None
    assert message.language == "en"


def test_message_rejects_blank_id() -> None:
    with pytest.raises(ValueError, match="message_id must not be empty"):
        Message(content="Hello", message_id=" ")


def test_message_requires_timezone_aware_creation_time() -> None:
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        Message(
            content="Hello",
            created_at=datetime(2030, 1, 1, tzinfo=UTC).replace(tzinfo=None),
        )
