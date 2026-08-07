from datetime import date

from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.graph.reducers import merge_information, merge_messages
from conversation.graph.state import ConversationMessage, MessageRole
from conversation.value_object.information_fields import InformationField


def entry(message_id: str, content: str) -> ConversationMessage:
    return ConversationMessage(
        MessageRole.USER,
        Message(content, message_id=message_id),
    )


def test_merge_messages_appends_new_entries_without_mutating_inputs() -> None:
    current = [entry("one", "First")]
    updates = [entry("two", "Second")]

    merged = merge_messages(current, updates)

    assert [item.message_id for item in merged] == ["one", "two"]
    assert len(current) == 1
    assert len(updates) == 1


def test_merge_messages_replaces_entry_in_original_position() -> None:
    current = [entry("one", "Old"), entry("two", "Second")]
    replacement = entry("one", "New")

    merged = merge_messages(current, [replacement])

    assert merged == [replacement, current[1]]


def test_merge_messages_accepts_none_inputs() -> None:
    assert merge_messages(None, None) == []


def test_merge_information_adds_and_replaces_without_mutation() -> None:
    old = Information(InformationField.FIRST_NAME, "Alex")
    new = Information(InformationField.FIRST_NAME, "Sam")
    check_in = Information(InformationField.CHECK_IN, date(2030, 1, 1))
    current = {InformationField.FIRST_NAME: old}
    updates = {
        InformationField.FIRST_NAME: new,
        InformationField.CHECK_IN: check_in,
    }

    merged = merge_information(current, updates)

    assert merged == {
        InformationField.FIRST_NAME: new,
        InformationField.CHECK_IN: check_in,
    }
    assert current == {InformationField.FIRST_NAME: old}


def test_merge_information_accepts_none_inputs() -> None:
    assert merge_information(None, None) == {}
