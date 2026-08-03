"""Supported booking statuses."""

from enum import StrEnum


class BookingStatus(StrEnum):
    """A booking status supported by the hotel."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

    @property
    def blocks_room(self) -> bool:
        """Return whether a booking with this status blocks a room."""

        return self in {
            BookingStatus.PENDING,
            BookingStatus.CONFIRMED,
        }