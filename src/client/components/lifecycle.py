"""Browser lifecycle bridge for best-effort tab-close termination."""

from __future__ import annotations

import json

import streamlit as st


def scroll_chat_to_latest(message_id: str, message_count: int) -> None:
    """Scroll once after Streamlit has committed the expected transcript."""

    encoded_message_id = json.dumps(message_id)
    st.html(
        f"""
        <script>
        (() => {{
          const messageId = {encoded_message_id};
          const expectedMessageCount = {message_count};
          if (window.__harbourLightLastScrollRequest === messageId) return;
          window.__harbourLightLastScrollRequest = messageId;

          const getViewport = () => document.querySelector(
              '[data-testid="stAppScrollToBottomContainer"]'
          );
          const hasExpectedTranscript = (viewport) =>
            viewport.querySelectorAll('[data-testid="stChatMessage"]').length ===
              expectedMessageCount;

          let settleTimer;
          let observer;
          let completed = false;
          const commitScroll = () => {{
            if (completed) return;
            const viewport = getViewport();
            if (!viewport || !hasExpectedTranscript(viewport)) return;
            completed = true;
            viewport.scrollTo({{top: viewport.scrollHeight, behavior: 'auto'}});
            window.__harbourLightLastAutoScroll = messageId;
            observer?.disconnect();
          }};

          const scheduleCommit = () => {{
            window.clearTimeout(settleTimer);
            settleTimer = window.setTimeout(commitScroll, 32);
          }};

          const viewport = getViewport();
          if (!viewport) return;
          observer = new MutationObserver(scheduleCommit);
          observer.observe(viewport, {{childList: true, subtree: true}});
          scheduleCommit();
          window.setTimeout(() => {{
            commitScroll();
            observer?.disconnect();
          }}, 1200);
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def focus_chat_input_on_load() -> None:
    """Focus the guest input once after a full browser-page load."""

    st.html(
        """
        <script>
        (() => {
          if (window.__harbourLightInitialInputFocusBound) return;
          window.__harbourLightInitialInputFocusBound = true;

          const focusInput = () => {
            const input = document.querySelector('[data-testid="stChatInput"] textarea');
            if (!input || input.disabled) return false;
            input.focus({preventScroll: true});
            return true;
          };

          if (focusInput()) return;
          const observer = new MutationObserver(() => {
            if (!focusInput()) return;
            observer.disconnect();
          });
          observer.observe(document.body, {childList: true, subtree: true});
          window.setTimeout(() => observer.disconnect(), 2000);
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def register_tab_close_termination(termination_url: str) -> None:
    """Queue a small POST when the page is left or the browser tab closes.

    Browsers do not guarantee delivery during shutdown. The server-side idle
    timeout remains the deterministic fallback for abandoned tabs.
    """

    encoded_url = json.dumps(termination_url)
    st.html(
        f"""
        <script>
        (() => {{
          window.__harbourLightTerminationUrl = {encoded_url};

          if (window.__harbourLightLifecycleBound) return;

          const terminate = () => {{
            const url = window.__harbourLightTerminationUrl;
            if (!url || window.__harbourLightTerminatedUrl === url) return;

            const queued = navigator.sendBeacon(url);
            if (queued) {{
              window.__harbourLightTerminatedUrl = url;
              return;
            }}

            fetch(url, {{
              method: "POST",
              keepalive: true,
              mode: "no-cors",
              credentials: "omit"
            }}).catch(() => undefined);
            window.__harbourLightTerminatedUrl = url;
          }};

          window.addEventListener("pagehide", terminate, {{capture: true}});
          window.__harbourLightLifecycleBound = true;
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )
