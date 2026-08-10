"""Small HTTP adapter for the conversation-only client boundary."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import cast
from urllib.parse import quote, urlsplit

import httpx

DEFAULT_API_URL = "http://127.0.0.1:8000/api/conversation"
API_URL_ENV = "CONCIERGE_API_URL"


class ConversationApiError(RuntimeError):
    """A guest-safe boundary error raised for any API transport failure."""


class ResponseKind(StrEnum):
    """Structured response shapes exposed by the current conversation API."""

    MESSAGE = "message"
    GREETING = "greeting"
    ERROR = "error"
    CONFIRMATION = "confirmation"
    AVAILABILITY = "availability"
    BOOKING = "booking"


@dataclass(frozen=True, slots=True)
class ConversationResponse:
    """Validated response data needed by the Streamlit presentation layer."""

    session_active: bool
    text: str
    kind: ResponseKind
    payload: dict[str, object]

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> ConversationResponse:
        """Classify a response by subclass-specific fields, never message text."""

        session_active = payload.get("session_active")
        text = payload.get("text")
        if not isinstance(session_active, bool) or not isinstance(text, str):
            raise ConversationApiError("Invalid conversation response")

        content = payload.get("content")
        if isinstance(payload.get("session_id"), str):
            kind = ResponseKind.GREETING
        elif isinstance(payload.get("reason"), str):
            kind = ResponseKind.ERROR
        elif "data" in payload:
            kind = ResponseKind.CONFIRMATION
        elif isinstance(content, dict) and isinstance(content.get("rooms"), list):
            kind = ResponseKind.AVAILABILITY
        elif isinstance(content, dict):
            kind = ResponseKind.BOOKING
        else:
            kind = ResponseKind.MESSAGE

        return cls(
            session_active=session_active,
            text=text,
            kind=kind,
            payload=payload,
        )

    @property
    def session_id(self) -> str | None:
        """Return the public conversation identifier from a greeting."""

        value = self.payload.get("session_id")
        return value if isinstance(value, str) else None

    def rooms(self) -> list[dict[str, object]]:
        """Return structured room-category options when present."""

        content = self.payload.get("content")
        if not isinstance(content, dict):
            return []
        raw_rooms = content.get("rooms")
        if not isinstance(raw_rooms, list):
            return []
        return [
            cast(dict[str, object], room)
            for room in raw_rooms
            if isinstance(room, dict)
        ]

    def structured_data(self, field: str) -> dict[str, object] | None:
        """Return one mapping-valued response field."""

        value = self.payload.get(field)
        return cast(dict[str, object], value) if isinstance(value, dict) else None


@dataclass(frozen=True, slots=True)
class ConversationApi:
    """HTTP client restricted to the `/api/conversation` route family."""

    base_url: str
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        normalized = self.base_url.rstrip("/")
        parsed = urlsplit(normalized)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path.rstrip("/") != "/api/conversation"
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "CONCIERGE_API_URL must be an absolute /api/conversation URL"
            )
        object.__setattr__(self, "base_url", normalized)

    @classmethod
    def from_environment(cls) -> ConversationApi:
        """Build the client from one optional deployment-specific URL."""

        return cls(os.getenv(API_URL_ENV, DEFAULT_API_URL))

    def initialize(self) -> ConversationResponse:
        """Start a new conversation session."""

        payload = self._post(f"{self.base_url}/")
        return ConversationResponse.from_payload(payload)

    def send_message(self, session_id: str, message: str) -> ConversationResponse:
        """Submit a URL-encoded message to an existing conversation."""

        payload = self._post(
            f"{self.base_url}/{quote(session_id, safe='')}",
            params={"message": message},
        )
        return ConversationResponse.from_payload(payload)

    def terminate(self, session_id: str) -> None:
        """Terminate an existing conversation; the operation is idempotent."""

        self._post(self.termination_url(session_id), expect_json=False)

    def termination_url(self, session_id: str) -> str:
        """Return the conversation-scoped URL used by unload delivery."""

        return f"{self.base_url}/{quote(session_id, safe='')}/terminate"

    def _post(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        expect_json: bool = True,
    ) -> dict[str, object]:
        try:
            response = httpx.post(
                url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            if not expect_json:
                return {}
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ConversationApiError("Conversation API request failed") from error

        if not isinstance(payload, dict):
            raise ConversationApiError("Invalid conversation response")
        return cast(dict[str, object], payload)
