"""Validated wire value for a hotel-information topic selected in the client."""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.information_topic import InformationTopic

_WIRE_PREFIX = "__concierge_information_topic_v1__"


@dataclass(frozen=True, slots=True)
class InformationTopicSelection:
    """One hotel-information topic selected in the trusted client UI."""

    topic: InformationTopic

    def to_wire(self) -> str:
        """Serialize this client action into a compact validated message."""

        return f"{_WIRE_PREFIX}|{self.topic.value}"

    @classmethod
    def from_wire(cls, message: str) -> InformationTopicSelection | None:
        """Parse one exact client action, returning ``None`` for normal text."""

        parts = message.split("|")
        if len(parts) != 2 or parts[0] != _WIRE_PREFIX:
            return None

        try:
            return cls(topic=InformationTopic(parts[1]))
        except ValueError:
            return None
