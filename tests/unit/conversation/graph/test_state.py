from conversation.entities.message import Message
from conversation.graph.state import ConversationMessage, MessageRole


def test_conversation_message_exposes_wrapped_message_id() -> None:
    message = Message("Hello", message_id="message-1")
    entry = ConversationMessage(MessageRole.USER, message)

    assert entry.message_id == "message-1"
