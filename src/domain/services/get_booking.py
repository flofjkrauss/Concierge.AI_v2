"""Service for retrieving a booking."""

from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from observability import LOG_MSG


def get_booking(
    booking_id: str,
    database: DatabaseInterface,
) -> Booking | None:
    """Return the booking with the given ID if it exists."""

    if not booking_id.strip():
        raise ValueError("booking_id must not be empty")

    booking = database.get_booking(booking_id)

    if booking is None:
        LOG_MSG.debug(
            f"No booking with ID {booking_id} was found.")

    return booking