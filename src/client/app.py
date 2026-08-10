"""Streamlit entry point for the Harbour Light Hotel concierge."""

from __future__ import annotations

import time
from pathlib import Path
from typing import cast

import streamlit as st

from client.components.api import (
    ConversationApi,
    ConversationApiError,
    ConversationResponse,
    ResponseKind,
)
from client.components.lifecycle import register_tab_close_termination
from client.components.models import ChatEntry, ChatRole
from client.components.views import apply_theme, render_header, render_transcript

APP_DIR = Path(__file__).resolve().parent
ASSET_DIR = APP_DIR / "assets"
INACTIVITY_TIMEOUT_SECONDS = 10 * 60
INACTIVITY_CHECK_SECONDS = 15.0

MESSAGES_KEY = "harbour_light_messages"
SESSION_ID_KEY = "harbour_light_session_id"
SESSION_ACTIVE_KEY = "harbour_light_session_active"
LAST_ACTIVITY_KEY = "harbour_light_last_activity"
CONSUMED_ACTIONS_KEY = "harbour_light_consumed_actions"
INITIALIZED_KEY = "harbour_light_initialized"

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
GENERIC_BACKEND_ERROR = (
    "I couldn't complete that request. Please start a new chat and try again."
)


def _initialize_local_state() -> None:
    defaults: dict[str, object] = {
        MESSAGES_KEY: [],
        SESSION_ID_KEY: None,
        SESSION_ACTIVE_KEY: False,
        LAST_ACTIVITY_KEY: time.monotonic(),
        CONSUMED_ACTIONS_KEY: set(),
        INITIALIZED_KEY: False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _messages() -> list[ChatEntry]:
    return cast(list[ChatEntry], st.session_state[MESSAGES_KEY])


def _consumed_actions() -> set[str]:
    return cast(set[str], st.session_state[CONSUMED_ACTIONS_KEY])


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
    if response.kind is ResponseKind.ERROR:
        return GENERIC_BACKEND_ERROR
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
    session_id = _ensure_remote_session(api)
    if api is None or session_id is None:
        return

    if source_message_id is not None:
        if source_message_id in _consumed_actions():
            return
        _consumed_actions().add(source_message_id)

    _append_message("user", visible_text)
    st.session_state[LAST_ACTIVITY_KEY] = time.monotonic()

    try:
        with st.spinner("One moment — I'm checking that for you."):
            response = api.send_message(session_id, api_text)
    except ConversationApiError:
        _append_message("assistant", TURN_FAILED)
        return

    _apply_response(response)


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
        if not _is_session_active():
            return
        last_activity = cast(float, st.session_state[LAST_ACTIVITY_KEY])
        if time.monotonic() - last_activity >= INACTIVITY_TIMEOUT_SECONDS:
            _expire_inactive_session(api)
            st.rerun()

    inactivity_watchdog()

    session_id = _session_id()
    if api is not None and session_id is not None and _is_session_active():
        register_tab_close_termination(api.termination_url(session_id))

    shortcut = render_transcript(
        _messages(),
        asset_dir=ASSET_DIR,
        session_active=_is_session_active(),
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

    prompt = st.chat_input(
        "Ask your concierge…",
        key="harbour_light_guest_input",
        max_chars=250,
        disabled=api is None,
    )
    if prompt:
        _submit_turn(api, visible_text=prompt, api_text=prompt)
        st.rerun()


if __name__ == "__main__":
    main()
