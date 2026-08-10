"""Small immutable view models used by the Streamlit client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from client.components.api import ConversationResponse

type ChatRole = Literal["assistant", "user"]


@dataclass(frozen=True, slots=True)
class ChatEntry:
    """One guest-visible message and its optional structured response."""

    role: ChatRole
    text: str
    response: ConversationResponse | None = None
    message_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True, slots=True)
class Shortcut:
    """A human-readable UI action plus its canonical API message."""

    visible_text: str
    api_text: str
    source_message_id: str
