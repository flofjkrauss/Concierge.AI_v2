"""Browser lifecycle bridge for best-effort tab-close termination."""

from __future__ import annotations

import json

import streamlit as st


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
