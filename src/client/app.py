"""Streamlit entry point for the Harbour Light Hotel concierge."""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import cast

import streamlit as st

from client.components.api import (
    ConversationApi,
    ConversationApiError,
    ConversationResponse,
    ResponseKind,
)
from client.components.lifecycle import (
    focus_chat_input_on_load,
    register_tab_close_termination,
    scroll_chat_to_latest,
)
from client.components.models import ChatEntry, ChatRole
from client.components.views import apply_theme, render_header, render_transcript
from configuration.application import ApplicationSettings

APP_DIR = Path(__file__).resolve().parent
ASSET_DIR = APP_DIR / "assets"
INACTIVITY_TIMEOUT_SECONDS = 10 * 60
INACTIVITY_CHECK_SECONDS = 15.0
PATIENCE_INTERVAL_SECONDS = max(
    0.5,
    ApplicationSettings.get_settings().conversation_patience_interval_seconds,
)
PENDING_TURN_CHECK_SECONDS = min(1.0, PATIENCE_INTERVAL_SECONDS / 4)

MESSAGES_KEY = "harbour_light_messages"
SESSION_ID_KEY = "harbour_light_session_id"
SESSION_ACTIVE_KEY = "harbour_light_session_active"
LAST_ACTIVITY_KEY = "harbour_light_last_activity"
CONSUMED_ACTIONS_KEY = "harbour_light_consumed_actions"
INITIALIZED_KEY = "harbour_light_initialized"
LAST_SCROLLED_MESSAGE_KEY = "harbour_light_last_scrolled_message"
PENDING_TURN_KEY = "harbour_light_pending_turn"
PENDING_TURN_STARTED_KEY = "harbour_light_pending_turn_started"
PENDING_TURN_MESSAGE_KEY = "harbour_light_pending_turn_message"
PATIENCE_SHOWN_KEY = "harbour_light_patience_shown"

SERVICE_UNAVAILABLE = (
    "The concierge service is unavailable right now. Please try a new chat in a moment."
)
TURN_FAILED = (
    "I couldn't reach the hotel service just now. Your chat is still open, "
    "so please try again."
)
SESSION_EXPIRED = (
    "This chat closed after 10 minutes of inactivity. Start a new chat "
    "whenever you're ready."
)


@st.cache_resource(show_spinner=False)
def _turn_executor() -> ThreadPoolExecutor:
    """Keep background workers stable across Streamlit script reruns."""

    return ThreadPoolExecutor(
        max_workers=4,
        thread_name_prefix="concierge-client-turn",
    )


def _initialize_local_state() -> None:
    defaults: dict[str, object] = {
        MESSAGES_KEY: [],
        SESSION_ID_KEY: None,
        SESSION_ACTIVE_KEY: False,
        LAST_ACTIVITY_KEY: time.monotonic(),
        CONSUMED_ACTIONS_KEY: set(),
        INITIALIZED_KEY: False,
        LAST_SCROLLED_MESSAGE_KEY: None,
        PENDING_TURN_KEY: None,
        PENDING_TURN_STARTED_KEY: None,
        PENDING_TURN_MESSAGE_KEY: None,
        PATIENCE_SHOWN_KEY: False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _messages() -> list[ChatEntry]:
    return cast(list[ChatEntry], st.session_state[MESSAGES_KEY])


def _consumed_actions() -> set[str]:
    return cast(set[str], st.session_state[CONSUMED_ACTIONS_KEY])


def _input_focus_request_id() -> str:
    """Return the latest assistant message that should restore input focus."""

    for message in reversed(_messages()):
        if message.role == "assistant":
            return message.message_id
    return "initial-load"


def _session_id() -> str | None:
    return cast(str | None, st.session_state[SESSION_ID_KEY])


def _is_session_active() -> bool:
    return cast(bool, st.session_state[SESSION_ACTIVE_KEY])


def _append_message(
    role: ChatRole,
    text: str,
    response: ConversationResponse | None = None,
) -> None:
    _messages().append(ChatEntry(role=role, text=text, response=response))


def _guest_text(response: ConversationResponse) -> str:
    return response.text


def _apply_response(response: ConversationResponse) -> None:
    _append_message("assistant", _guest_text(response), response)
    st.session_state[SESSION_ACTIVE_KEY] = response.session_active


def _initialize_remote_session(api: ConversationApi | None) -> None:
    st.session_state[INITIALIZED_KEY] = True
    st.session_state[LAST_ACTIVITY_KEY] = time.monotonic()

    if api is None:
        _append_message("assistant", SERVICE_UNAVAILABLE)
        return

    try:
        with st.spinner("Opening your concierge chat…"):
            response = api.initialize()
    except ConversationApiError:
        _append_message("assistant", SERVICE_UNAVAILABLE)
        return

    session_id = response.session_id
    if session_id is None or response.kind is not ResponseKind.GREETING:
        _append_message("assistant", SERVICE_UNAVAILABLE)
        return

    st.session_state[SESSION_ID_KEY] = session_id
    _apply_response(response)


def _terminate_remote_session(api: ConversationApi | None) -> None:
    session_id = _session_id()
    if api is None or session_id is None:
        return
    try:
        api.terminate(session_id)
    except ConversationApiError:
        # Browser close and local cleanup are intentionally best effort.
        pass


def _ensure_remote_session(api: ConversationApi | None) -> str | None:
    """Return an active session, initializing one when the client has none."""

    session_id = _session_id()
    if api is not None and session_id is not None and _is_session_active():
        return session_id
    if api is None:
        return None

    st.session_state[SESSION_ID_KEY] = None
    st.session_state[SESSION_ACTIVE_KEY] = False
    st.session_state[INITIALIZED_KEY] = False
    _initialize_remote_session(api)

    session_id = _session_id()
    if session_id is None or not _is_session_active():
        return None
    return session_id


def _submit_turn(
    api: ConversationApi | None,
    *,
    visible_text: str,
    api_text: str,
    source_message_id: str | None = None,
) -> None:
    if _has_pending_turn():
        return

    session_id = _ensure_remote_session(api)
    if api is None or session_id is None:
        return

    if source_message_id is not None:
        if source_message_id in _consumed_actions():
            return
        _consumed_actions().add(source_message_id)

    _append_message("user", visible_text)
    st.session_state[LAST_ACTIVITY_KEY] = time.monotonic()

    future = _turn_executor().submit(api.send_message, session_id, api_text)
    st.session_state[PENDING_TURN_KEY] = future
    st.session_state[PENDING_TURN_STARTED_KEY] = time.monotonic()
    st.session_state[PENDING_TURN_MESSAGE_KEY] = api_text
    st.session_state[PATIENCE_SHOWN_KEY] = False

    try:
        # Preserve immediate responses without making normal model turns blocking.
        future.result(timeout=0.01)
    except TimeoutError:
        return
    except Exception:  # noqa: BLE001
        _complete_pending_turn(future)
        return

    _complete_pending_turn(future)


def _has_pending_turn() -> bool:
    return isinstance(st.session_state.get(PENDING_TURN_KEY), Future)


def _clear_pending_turn() -> None:
    st.session_state[PENDING_TURN_KEY] = None
    st.session_state[PENDING_TURN_STARTED_KEY] = None
    st.session_state[PENDING_TURN_MESSAGE_KEY] = None
    st.session_state[PATIENCE_SHOWN_KEY] = False


def _complete_pending_turn(
    future: Future[ConversationResponse],
) -> None:
    """Consume one completed background request without leaking exceptions."""

    try:
        response = future.result()
        if not isinstance(response, ConversationResponse):
            raise ConversationApiError("Invalid conversation response")
    except Exception:  # noqa: BLE001
        _append_message("assistant", TURN_FAILED)
    else:
        _apply_response(response)
    finally:
        _clear_pending_turn()


def _poll_pending_turn(api: ConversationApi | None) -> bool:
    """Update the transcript when a background turn progresses or completes."""

    future = st.session_state.get(PENDING_TURN_KEY)
    if not isinstance(future, Future):
        return False

    if future.done():
        _complete_pending_turn(cast(Future[ConversationResponse], future))
        return True

    started = st.session_state.get(PENDING_TURN_STARTED_KEY)
    if (
        api is None
        or not isinstance(started, float)
        or cast(bool, st.session_state.get(PATIENCE_SHOWN_KEY, False))
        or time.monotonic() - started < PATIENCE_INTERVAL_SECONDS
    ):
        return False

    session_id = _session_id()
    pending_message = st.session_state.get(PENDING_TURN_MESSAGE_KEY)
    if session_id is None or not isinstance(pending_message, str):
        return False

    try:
        progress = api.patience_message(session_id, pending_message)
    except ConversationApiError:
        return False

    _append_message("assistant", progress.text, progress)
    st.session_state[PATIENCE_SHOWN_KEY] = True
    return True


def _expire_inactive_session(api: ConversationApi | None) -> None:
    if not _is_session_active():
        return
    _terminate_remote_session(api)
    st.session_state[SESSION_ACTIVE_KEY] = False
    _append_message("assistant", SESSION_EXPIRED)


def _api_from_environment() -> ConversationApi | None:
    try:
        return ConversationApi.from_environment()
    except ValueError:
        return None


def _request_scroll_to_latest_message() -> None:
    """Request one auto-scroll when the latest rendered message changes."""

    messages = _messages()
    if not messages:
        return
    latest_message_id = messages[-1].message_id
    if st.session_state[LAST_SCROLLED_MESSAGE_KEY] == latest_message_id:
        return
    scroll_chat_to_latest(latest_message_id, len(messages))
    st.session_state[LAST_SCROLLED_MESSAGE_KEY] = latest_message_id


def _submit_chat_input(api: ConversationApi | None) -> None:
    """Submit the keyed chat input before Streamlit renders the next frame."""

    prompt = st.session_state.get("harbour_light_guest_input")
    if isinstance(prompt, str) and prompt.strip():
        _submit_turn(api, visible_text=prompt, api_text=prompt)


def main() -> None:
    """Render the full-height guest chat and coordinate its API session."""

    st.set_page_config(
        page_title="Harbour Light Hotel Concierge",
        page_icon=str(ASSET_DIR / "harbour-light-mark.svg"),
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    apply_theme(
        ASSET_DIR / "theme.css",
        ASSET_DIR / "harbour-background.png",
        ASSET_DIR / "harbour-gold-lines.svg",
    )
    _initialize_local_state()
    api = _api_from_environment()

    render_header(ASSET_DIR / "harbour-light-hotel-logo.svg")

    if not cast(bool, st.session_state[INITIALIZED_KEY]):
        _initialize_remote_session(api)

    @st.fragment(run_every=INACTIVITY_CHECK_SECONDS)
    def inactivity_watchdog() -> None:
        if not _is_session_active() or _has_pending_turn():
            return
        last_activity = cast(float, st.session_state[LAST_ACTIVITY_KEY])
        if time.monotonic() - last_activity >= INACTIVITY_TIMEOUT_SECONDS:
            _expire_inactive_session(api)
            st.rerun()

    inactivity_watchdog()

    @st.fragment(run_every=PENDING_TURN_CHECK_SECONDS)
    def pending_turn_watchdog() -> None:
        if _poll_pending_turn(api):
            st.rerun()

    pending_turn_watchdog()

    session_id = _session_id()
    if api is not None and session_id is not None and _is_session_active():
        register_tab_close_termination(api.termination_url(session_id))

    shortcut = render_transcript(
        _messages(),
        asset_dir=ASSET_DIR,
        actions_enabled=_is_session_active() and not _has_pending_turn(),
        consumed_actions=_consumed_actions(),
    )
    if shortcut is not None:
        _submit_turn(
            api,
            visible_text=shortcut.visible_text,
            api_text=shortcut.api_text,
            source_message_id=shortcut.source_message_id,
        )
        st.rerun()

    st.chat_input(
        "Ask your concierge…",
        key="harbour_light_guest_input",
        max_chars=250,
        disabled=api is None or _has_pending_turn(),
        on_submit=_submit_chat_input,
        args=(api,),
    )
    _request_scroll_to_latest_message()
    focus_chat_input_on_load(_input_focus_request_id())


if __name__ == "__main__":
    main()
