"""Validated wire value for a room selection made in the trusted client UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod

_WIRE_PREFIX = "__concierge_booking_selection_v1__"


@dataclass(frozen=True, slots=True)
class BookingSelection:
    """One room category selected for immutable availability criteria."""

    check_in: date
    check_out: date
    guest_count: int
    accessible: bool
    room_category: RoomCategory

    def __post_init__(self) -> None:
        StayPeriod(self.check_in, self.check_out)
        if self.guest_count < 1:
            raise ValueError("guest_count must be at least 1")

    def to_wire(self) -> str:
        """Serialize this client action into a compact validated message."""

        accessible = "false"
        if self.accessible:
            accessible = "true"

        return "|".join(
            (
                _WIRE_PREFIX,
                self.check_in.isoformat(),
                self.check_out.isoformat(),
                str(self.guest_count),
                accessible,
                self.room_category.value,
            )
        )

    @classmethod
    def from_wire(cls, message: str) -> BookingSelection | None:
        """Parse one exact client action, returning ``None`` for normal text."""

        parts = message.split("|")
        if not parts or parts[0] != _WIRE_PREFIX:
            return None
        if len(parts) != 6 or parts[4] not in {"true", "false"}:
            return None

        try:
            return cls(
                check_in=date.fromisoformat(parts[1]),
                check_out=date.fromisoformat(parts[2]),
                guest_count=int(parts[3]),
                accessible=parts[4] == "true",
                room_category=RoomCategory(parts[5]),
            )
        except (TypeError, ValueError):
            return None
