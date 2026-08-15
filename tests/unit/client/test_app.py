"""Tests for Streamlit conversation-session recovery."""

from concurrent.futures import Future
from contextlib import nullcontext
from unittest.mock import Mock, call

import pytest

from client import app as client_app
from client.components.api import (
    ConversationApi,
    ConversationApiError,
    ConversationResponse,
)
from client.components.models import ChatEntry, Shortcut


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


def _local_state(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    session_state: dict[str, object] = {}
    monkeypatch.setattr(client_app.st, "session_state", session_state)
    monkeypatch.setattr(client_app.st, "spinner", lambda _: nullcontext())
    client_app._initialize_local_state()
    return session_state


@pytest.mark.parametrize("api_failure", [False, True])
def test_initialize_remote_session_reports_unavailable_service(
    monkeypatch: pytest.MonkeyPatch,
    api_failure: bool,
) -> None:
    session_state = _local_state(monkeypatch)
    api: ConversationApi | None = None
    if api_failure:
        api = Mock(spec=ConversationApi)
        api.initialize.side_effect = ConversationApiError("offline")

    client_app._initialize_remote_session(api)

    assert session_state[client_app.INITIALIZED_KEY] is True
    assert client_app._messages()[-1].text == client_app.SERVICE_UNAVAILABLE
    assert session_state[client_app.SESSION_ID_KEY] is None


def test_initialize_remote_session_rejects_non_greeting_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _local_state(monkeypatch)
    api = Mock(spec=ConversationApi)
    api.initialize.return_value = ConversationResponse.from_payload(
        {"session_active": True, "text": "Missing session id"}
    )

    client_app._initialize_remote_session(api)

    assert client_app._messages()[-1].text == client_app.SERVICE_UNAVAILABLE
    assert client_app._session_id() is None


def test_terminate_remote_session_is_best_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = _local_state(monkeypatch)
    session_state[client_app.SESSION_ID_KEY] = "session-1"
    api = Mock(spec=ConversationApi)
    api.terminate.side_effect = ConversationApiError("offline")

    client_app._terminate_remote_session(api)

    api.terminate.assert_called_once_with("session-1")


def test_submit_turn_consumes_shortcut_only_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = _local_state(monkeypatch)
    session_state[client_app.SESSION_ID_KEY] = "session-1"
    session_state[client_app.SESSION_ACTIVE_KEY] = True
    api = Mock(spec=ConversationApi)
    api.send_message.return_value = ConversationResponse.from_payload(
        {"session_active": True, "text": "Selected"}
    )

    client_app._submit_turn(
        api,
        visible_text="Select Deluxe Room",
        api_text="booking wire",
        source_message_id="option-1",
    )
    client_app._submit_turn(
        api,
        visible_text="Select Deluxe Room",
        api_text="booking wire",
        source_message_id="option-1",
    )

    api.send_message.assert_called_once_with("session-1", "booking wire")
    assert client_app._consumed_actions() == {"option-1"}


def test_complete_pending_turn_applies_response_and_clears_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = _local_state(monkeypatch)
    future: Future[ConversationResponse] = Future()
    response = ConversationResponse.from_payload(
        {"session_active": False, "text": "Goodbye"}
    )
    future.set_result(response)
    session_state[client_app.PENDING_TURN_KEY] = future
    session_state[client_app.PATIENCE_SHOWN_KEY] = True

    client_app._complete_pending_turn(future)

    assert client_app._messages()[-1].response is response
    assert session_state[client_app.SESSION_ACTIVE_KEY] is False
    assert session_state[client_app.PENDING_TURN_KEY] is None
    assert session_state[client_app.PATIENCE_SHOWN_KEY] is False


@pytest.mark.parametrize("invalid_result", [None, "not a response"])
def test_complete_pending_turn_turns_invalid_result_into_safe_message(
    monkeypatch: pytest.MonkeyPatch,
    invalid_result: object,
) -> None:
    _local_state(monkeypatch)
    future: Future[object] = Future()
    future.set_result(invalid_result)

    client_app._complete_pending_turn(future)  # type: ignore[arg-type]

    assert client_app._messages()[-1].text == client_app.TURN_FAILED


def test_poll_pending_turn_adds_patience_message_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = _local_state(monkeypatch)
    future: Future[ConversationResponse] = Future()
    session_state.update(
        {
            client_app.SESSION_ID_KEY: "session-1",
            client_app.PENDING_TURN_KEY: future,
            client_app.PENDING_TURN_STARTED_KEY: 10.0,
            client_app.PENDING_TURN_MESSAGE_KEY: "Find a room",
        }
    )
    monkeypatch.setattr(client_app.time, "monotonic", lambda: 20.0)
    monkeypatch.setattr(client_app, "PATIENCE_INTERVAL_SECONDS", 5.0)
    api = Mock(spec=ConversationApi)
    progress = ConversationResponse.from_payload(
        {"session_active": True, "text": "Still checking availability."}
    )
    api.patience_message.return_value = progress

    assert client_app._poll_pending_turn(api) is True
    assert client_app._poll_pending_turn(api) is False

    api.patience_message.assert_called_once_with("session-1", "Find a room")
    assert client_app._messages()[-1].response is progress


def test_poll_pending_turn_handles_completed_future(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = _local_state(monkeypatch)
    future: Future[ConversationResponse] = Future()
    future.set_result(
        ConversationResponse.from_payload(
            {"session_active": True, "text": "Complete"}
        )
    )
    session_state[client_app.PENDING_TURN_KEY] = future

    assert client_app._poll_pending_turn(None) is True
    assert client_app._messages()[-1].text == "Complete"
    assert client_app._has_pending_turn() is False


def test_expire_inactive_session_terminates_and_closes_locally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = _local_state(monkeypatch)
    session_state[client_app.SESSION_ID_KEY] = "session-1"
    session_state[client_app.SESSION_ACTIVE_KEY] = True
    api = Mock(spec=ConversationApi)

    client_app._expire_inactive_session(api)

    api.terminate.assert_called_once_with("session-1")
    assert session_state[client_app.SESSION_ACTIVE_KEY] is False
    assert client_app._messages()[-1].text == client_app.SESSION_EXPIRED


def test_api_from_environment_returns_none_for_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        client_app.ConversationApi,
        "from_environment",
        Mock(side_effect=ValueError("invalid URL")),
    )

    assert client_app._api_from_environment() is None


def test_input_focus_uses_latest_assistant_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _local_state(monkeypatch)
    assert client_app._input_focus_request_id() == "initial-load"
    client_app._messages().extend(
        [
            ChatEntry(role="assistant", text="Welcome", message_id="assistant-1"),
            ChatEntry(role="user", text="Hello", message_id="user-1"),
        ]
    )

    assert client_app._input_focus_request_id() == "assistant-1"


def _mock_main_streamlit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_app.st, "set_page_config", Mock())
    monkeypatch.setattr(client_app.st, "fragment", lambda **_: lambda function: function)
    monkeypatch.setattr(client_app.st, "chat_input", Mock())
    monkeypatch.setattr(client_app.st, "rerun", Mock())
    monkeypatch.setattr(client_app, "apply_theme", Mock())
    monkeypatch.setattr(client_app, "render_header", Mock())
    monkeypatch.setattr(client_app, "focus_chat_input_on_load", Mock())
    monkeypatch.setattr(client_app, "scroll_chat_to_latest", Mock())


def test_main_renders_unavailable_concierge_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state: dict[str, object] = {}
    monkeypatch.setattr(client_app.st, "session_state", session_state)
    monkeypatch.setattr(client_app.st, "spinner", lambda _: nullcontext())
    _mock_main_streamlit(monkeypatch)
    transcript = Mock(return_value=None)
    monkeypatch.setattr(client_app, "render_transcript", transcript)
    monkeypatch.setattr(client_app, "_api_from_environment", lambda: None)

    client_app.main()

    client_app.st.set_page_config.assert_called_once()
    client_app.apply_theme.assert_called_once()
    client_app.render_header.assert_called_once()
    assert client_app._messages()[-1].text == client_app.SERVICE_UNAVAILABLE
    assert transcript.call_args.kwargs["session_active"] is False
    assert client_app.st.chat_input.call_args.kwargs["disabled"] is True
    client_app.focus_chat_input_on_load.assert_called_once()


def test_main_submits_selected_transcript_shortcut(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shortcut = Shortcut("Select Double Room", "selection wire", "rooms-1")
    session_state: dict[str, object] = {
        client_app.MESSAGES_KEY: [],
        client_app.SESSION_ID_KEY: "session-1",
        client_app.SESSION_ACTIVE_KEY: True,
        client_app.LAST_ACTIVITY_KEY: 10.0,
        client_app.CONSUMED_ACTIONS_KEY: set(),
        client_app.INITIALIZED_KEY: True,
    }
    monkeypatch.setattr(client_app.st, "session_state", session_state)
    _mock_main_streamlit(monkeypatch)
    api = Mock(spec=ConversationApi)
    submit = Mock()
    register = Mock()
    monkeypatch.setattr(client_app.time, "monotonic", lambda: 11.0)
    monkeypatch.setattr(client_app, "_api_from_environment", lambda: api)
    monkeypatch.setattr(client_app, "render_transcript", Mock(return_value=shortcut))
    monkeypatch.setattr(client_app, "_submit_turn", submit)
    monkeypatch.setattr(client_app, "register_tab_close_termination", register)
    api.termination_url.return_value = "https://hotel.test/terminate"

    client_app.main()

    register.assert_called_once_with("https://hotel.test/terminate")
    submit.assert_called_once_with(
        api,
        visible_text="Select Double Room",
        api_text="selection wire",
        source_message_id="rooms-1",
    )
    client_app.st.rerun.assert_called_once()
    assert client_app.st.chat_input.call_args.kwargs["disabled"] is False


def test_main_watchdog_expires_inactive_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state: dict[str, object] = {
        client_app.MESSAGES_KEY: [],
        client_app.SESSION_ID_KEY: "session-1",
        client_app.SESSION_ACTIVE_KEY: True,
        client_app.LAST_ACTIVITY_KEY: 0.0,
        client_app.CONSUMED_ACTIONS_KEY: set(),
        client_app.INITIALIZED_KEY: True,
    }
    monkeypatch.setattr(client_app.st, "session_state", session_state)
    _mock_main_streamlit(monkeypatch)
    api = Mock(spec=ConversationApi)
    expire = Mock()
    monkeypatch.setattr(client_app.time, "monotonic", lambda: 1000.0)
    monkeypatch.setattr(client_app, "_api_from_environment", lambda: api)
    monkeypatch.setattr(client_app, "_expire_inactive_session", expire)
    monkeypatch.setattr(client_app, "render_transcript", Mock(return_value=None))
    monkeypatch.setattr(client_app, "register_tab_close_termination", Mock())

    client_app.main()

    expire.assert_called_once_with(api)
    client_app.st.rerun.assert_called_once()
