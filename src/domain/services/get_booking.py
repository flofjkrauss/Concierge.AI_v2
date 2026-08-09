"""Service for retrieving a booking."""

from datetime import date

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

def get_booking_by_name(
        last_name: str,
        email: str,
        check_in: date,
        database: DatabaseInterface
) -> Booking | None:
    """Return the booking with the given last_name email combination if it exists."""

    if not last_name:
        raise ValueError("last_name must not be empty")
    if not email:
        raise ValueError("email must not be empty")
    if not check_in:
        raise ValueError("check_in must not be empty")
    if not isinstance(check_in, date):
        raise TypeError("check_in must be a date object")

    return database.get_booking_by_name(last_name=last_name, email=email, check_in=check_in)
    