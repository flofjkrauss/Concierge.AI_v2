"""Tests for Streamlit conversation-session recovery."""

from contextlib import nullcontext
from unittest.mock import Mock, call

import pytest

from client import app as client_app
from client.components.api import ConversationApi, ConversationResponse
from client.components.models import ChatEntry


def test_submit_turn_initializes_missing_session_before_sending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state: dict[str, object] = {}
    monkeypatch.setattr(client_app.st, "session_state", session_state)
    monkeypatch.setattr(client_app.st, "spinner", lambda _: nullcontext())
    client_app._initialize_local_state()

    api = Mock(spec=ConversationApi)
    api.initialize.return_value = ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Welcome",
            "session_id": "new-session",
        }
    )
    api.send_message.return_value = ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Your request was received.",
        }
    )

    client_app._submit_turn(
        api,
        visible_text="I need a quiet room.",
        api_text="I need a quiet room.",
    )

    assert api.mock_calls == [
        call.initialize(),
        call.send_message("new-session", "I need a quiet room."),
    ]
    assert session_state[client_app.SESSION_ID_KEY] == "new-session"
    assert [message.text for message in client_app._messages()] == [
        "Welcome",
        "I need a quiet room.",
        "Your request was received.",
    ]


def test_submit_turn_reuses_active_session(monkeypatch: pytest.MonkeyPatch) -> None:
    session_state: dict[str, object] = {
        client_app.MESSAGES_KEY: [],
        client_app.SESSION_ID_KEY: "active-session",
        client_app.SESSION_ACTIVE_KEY: True,
        client_app.LAST_ACTIVITY_KEY: 0.0,
        client_app.CONSUMED_ACTIONS_KEY: set(),
        client_app.INITIALIZED_KEY: True,
    }
    monkeypatch.setattr(client_app.st, "session_state", session_state)
    monkeypatch.setattr(client_app.st, "spinner", lambda _: nullcontext())

    api = Mock(spec=ConversationApi)
    api.send_message.return_value = ConversationResponse.from_payload(
        {"session_active": True, "text": "Received"}
    )

    client_app._submit_turn(api, visible_text="Hello", api_text="Hello")

    api.initialize.assert_not_called()
    api.send_message.assert_called_once_with("active-session", "Hello")


def test_scroll_is_requested_once_for_each_latest_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = ChatEntry(role="assistant", text="First", message_id="message-1")
    messages = [first]
    session_state: dict[str, object] = {
        client_app.MESSAGES_KEY: messages,
        client_app.LAST_SCROLLED_MESSAGE_KEY: None,
    }
    scroll = Mock()
    monkeypatch.setattr(client_app.st, "session_state", session_state)
    monkeypatch.setattr(client_app, "scroll_chat_to_latest", scroll)

    client_app._request_scroll_to_latest_message()
    client_app._request_scroll_to_latest_message()
    messages.append(
        ChatEntry(role="assistant", text="Second", message_id="message-2")
    )
    client_app._request_scroll_to_latest_message()

    assert scroll.call_args_list == [
        call("message-1", 1),
        call("message-2", 2),
    ]


def test_submit_chat_input_uses_keyed_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = Mock(spec=ConversationApi)
    session_state = {"harbour_light_guest_input": "A quiet room, please."}
    submit = Mock()
    monkeypatch.setattr(client_app.st, "session_state", session_state)
    monkeypatch.setattr(client_app, "_submit_turn", submit)

    client_app._submit_chat_input(api)

    submit.assert_called_once_with(
        api,
        visible_text="A quiet room, please.",
        api_text="A quiet room, please.",
    )
