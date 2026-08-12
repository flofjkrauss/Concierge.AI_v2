"""Small immutable view models used by the Streamlit client."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Literal, cast
from uuid import uuid4

from client.components.api import ConversationResponse
from conversation.value_object.booking_selection import BookingSelection
from domain.value_objects.room_category import RoomCategory

type ChatRole = Literal["assistant", "user"]

_INFORMATION_WIRE_PATTERN = re.compile(
    r"^\((?P<topic>[a-z][a-z0-9_]*)\)(?P<answer>.+)$",
    flags=re.IGNORECASE | re.DOTALL,
)


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


@dataclass(frozen=True, slots=True)
class AvailabilitySelectionData:
    """Immutable search criteria belonging to one availability response."""

    check_in: str
    check_out: str
    guest_count: int
    accessible: bool

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, object],
    ) -> AvailabilitySelectionData | None:
        """Validate criteria before exposing a booking shortcut."""

        check_in = _string_field(data, "check_in")
        check_out = _string_field(data, "check_out")
        guest_count = _integer_field(data, "guest_count")
        accessible = _boolean_field(data, "accessible")
        if (
            check_in is None
            or check_out is None
            or guest_count is None
            or guest_count < 1
            or accessible is None
        ):
            return None

        try:
            check_in_date = date.fromisoformat(check_in)
            check_out_date = date.fromisoformat(check_out)
        except ValueError:
            return None
        if check_out_date <= check_in_date:
            return None

        return cls(
            check_in=check_in,
            check_out=check_out,
            guest_count=guest_count,
            accessible=accessible,
        )

    def booking_message(self, room_category: str) -> str:
        """Build the deterministic booking action for one room category."""

        return BookingSelection(
            check_in=date.fromisoformat(self.check_in),
            check_out=date.fromisoformat(self.check_out),
            guest_count=self.guest_count,
            accessible=self.accessible,
            room_category=RoomCategory(room_category),
        ).to_wire()


@dataclass(frozen=True, slots=True)
class InformationCardData:
    """One structured hotel-information answer for the guest UI."""

    topic: str
    answer: str
    title: str | None

    @classmethod
    def from_mapping(cls, data: dict[str, object]) -> InformationCardData | None:
        """Normalize a structured information response from the conversation API."""

        topic = _string_field(data, "topic")
        answer = _string_field(data, "answer")
        if topic is None or answer is None:
            return None
        return cls(
            topic=topic.casefold(),
            answer=answer,
            title=_string_field(data, "title"),
        )

    @classmethod
    def from_wire_text(cls, text: str) -> InformationCardData | None:
        """Parse the explicit ``(topic)answer`` conversation wire format."""

        match = _INFORMATION_WIRE_PATTERN.fullmatch(text.strip())
        if match is None:
            return None
        answer = match.group("answer").strip()
        if not answer:
            return None
        return cls(
            topic=match.group("topic").casefold(),
            answer=answer,
            title=None,
        )


@dataclass(frozen=True, slots=True)
class BookingCardData:
    """Normalized booking data shared by previews and completed bookings."""

    booking_id: str | None
    status: str | None
    room_category: str | None
    guest_name: str | None
    guest_count: int | None
    check_in: str | None
    check_out: str | None
    total_price: dict[str, object] | None
    breakfast: bool | None
    accessible: bool | None
    email: str | None
    phone: str | None
    hotel_name: str | None
    hotel_address: str | None

    @classmethod
    def from_mapping(cls, data: dict[str, object]) -> BookingCardData | None:
        """Build one view model from either supported booking response shape."""

        recognized_fields = {
            "booking_id",
            "status",
            "room_category",
            "guest_name",
            "guest_count",
            "guests",
            "check_in",
            "arrival",
            "check_out",
            "departure",
            "total_prize",
            "total_price",
        }
        if not recognized_fields.intersection(data):
            return None

        first_name = _string_field(data, "first_name")
        last_name = _string_field(data, "last_name")
        guest_name = _string_field(data, "guest_name")
        if guest_name is None:
            guest_name = " ".join(
                part for part in (first_name, last_name) if part is not None
            ) or None

        return cls(
            booking_id=_string_field(data, "booking_id"),
            status=_string_field(data, "status"),
            room_category=_string_field(data, "room_category"),
            guest_name=guest_name,
            guest_count=_integer_field(data, "guest_count", "guests"),
            check_in=_string_field(data, "check_in", "arrival"),
            check_out=_string_field(data, "check_out", "departure"),
            total_price=_mapping_field(data, "total_price", "total_prize"),
            breakfast=_boolean_field(data, "breakfast", "breakfast_included"),
            accessible=_boolean_field(data, "accessible", "is_accessible"),
            email=_string_field(data, "email"),
            phone=_string_field(data, "phone"),
            hotel_name=_string_field(data, "hotel_name"),
            hotel_address=_string_field(data, "hotel_address"),
        )

    @property
    def is_cancellation_candidate(self) -> bool:
        """Return whether a confirmation concerns an existing booking."""

        normalized_status = self.status.casefold() if self.status is not None else None
        return self.booking_id is not None or normalized_status in {
            "confirmed",
            "cancelled",
        }


def _field(data: dict[str, object], *names: str) -> object | None:
    for name in names:
        if name not in data:
            continue
        value = data[name]
        if isinstance(value, dict) and "content" in value:
            return value.get("content")
        return value
    return None


def _string_field(data: dict[str, object], *names: str) -> str | None:
    value = _field(data, *names)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _integer_field(data: dict[str, object], *names: str) -> int | None:
    value = _field(data, *names)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _boolean_field(data: dict[str, object], *names: str) -> bool | None:
    value = _field(data, *names)
    return value if isinstance(value, bool) else None


def _mapping_field(
    data: dict[str, object],
    *names: str,
) -> dict[str, object] | None:
    value = _field(data, *names)
    return cast(dict[str, object], value) if isinstance(value, dict) else None
