from datetime import UTC, datetime

import pytest

from conversation.data_collector import DataCollector
from conversation.entities.message import Message
from conversation.entities.session import Session
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


def test_session_defaults_to_active_conversation_state() -> None:
    session = Session(collector=DataCollector())

    assert session.current_intent is Intent.CONVERSATION_INITIATION
    assert session.unknown_counter == 0
    assert session.messages == {}
    assert session.created_at.tzinfo is not None


def test_session_rejects_blank_id() -> None:
    with pytest.raises(ValueError, match="session_id must not be empty"):
        Session(collector=DataCollector(), session_id=" ")


def test_session_requires_timezone_aware_creation_time() -> None:
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        Session(
            collector=DataCollector(),
            created_at=datetime(2030, 1, 1, tzinfo=UTC).replace(tzinfo=None),
        )


def test_session_requires_data_collector() -> None:
    with pytest.raises(TypeError, match="collector must be of Type DataCollector"):
        Session(collector=object())  # type: ignore[arg-type]


@pytest.mark.parametrize("intent", [Intent.UNKNOWN, Intent.INFORMATION_REQUEST])
def test_session_rejects_transient_current_intents(intent: Intent) -> None:
    with pytest.raises(ValueError, match="current intent must not be"):
        Session(collector=DataCollector(), current_intent=intent)


def test_session_manages_unknown_counter() -> None:
    session = Session(collector=DataCollector())

    assert session.increase_unknown_counter() == 1
    assert session.increase_unknown_counter() == 2
    assert session.reset_unknown_counter() == 0


def test_session_stores_messages_by_id() -> None:
    session = Session(collector=DataCollector())
    message = Message("Hello", message_id="message-1")

    session.add_message(message)

    assert session.messages == {"message-1": message}


def test_session_reset_activates_new_intent_and_clears_missing_fields() -> None:
    session = Session(collector=DataCollector())
    session.last_intent_fullfilled = True
    session.missing_fields.append(InformationField.EMAIL)

    session.reset(Intent.BOOKING_REQUEST)

    assert session.current_intent is Intent.BOOKING_REQUEST
    assert not session.last_intent_fullfilled
    assert session.missing_fields == []
