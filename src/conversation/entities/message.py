"""conversation entity."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from configuration.application import ApplicationSettings


@dataclass(slots=True)
class Message:
    """message object"""
    content: str
    original_content: str = ""
    language: str = ApplicationSettings.get_settings().domain_language
    message_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.message_id.strip():
            raise ValueError("message_id must not be empty")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")