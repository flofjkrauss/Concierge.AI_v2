"""Tests for browser-side conversation lifecycle helpers."""

from unittest.mock import Mock

import pytest

from client.components import lifecycle


def test_scroll_chat_to_latest_targets_conversation_viewport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = Mock()
    monkeypatch.setattr(lifecycle.st, "html", html)

    lifecycle.scroll_chat_to_latest("message-1", 4)

    markup = html.call_args.args[0]
    assert 'stAppScrollToBottomContainer' in markup
    assert "expectedMessageCount = 4" in markup
    assert "hasExpectedTranscript" in markup
    assert "observer.observe(viewport" in markup
    assert "observer.observe(document.body" not in markup
    assert "behavior: 'auto'" in markup
    assert "behavior: 'smooth'" not in markup
    assert '"message-1"' in markup
    assert html.call_args.kwargs == {"unsafe_allow_javascript": True}


def test_focus_chat_input_uses_prevent_scroll_and_runs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = Mock()
    monkeypatch.setattr(lifecycle.st, "html", html)

    lifecycle.focus_chat_input_on_load()

    markup = html.call_args.args[0]
    assert 'stChatInput' in markup
    assert '__harbourLightInitialInputFocusBound' in markup
    assert 'focus({preventScroll: true})' in markup
    assert html.call_args.kwargs == {"unsafe_allow_javascript": True}


def test_tab_close_registers_beacon_with_keepalive_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = Mock()
    monkeypatch.setattr(lifecycle.st, "html", html)

    lifecycle.register_tab_close_termination(
        "https://hotel.test/api/conversation/session-1/terminate"
    )

    markup = html.call_args.args[0]
    assert "navigator.sendBeacon(url)" in markup
    assert 'method: "POST"' in markup
    assert "keepalive: true" in markup
    assert 'window.addEventListener("pagehide"' in markup
    assert '"https://hotel.test/api/conversation/session-1/terminate"' in markup
    assert html.call_args.kwargs == {"unsafe_allow_javascript": True}
