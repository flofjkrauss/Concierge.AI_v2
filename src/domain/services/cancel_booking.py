"""Service for cancelling a booking."""

from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.services.get_booking import get_booking
from domain.value_objects.booking_status import BookingStatus
from observability import LOG_MSG


def cancel_booking(
    booking_id: str,
    database: DatabaseInterface,
) -> Booking | None:
    """Cancel and persist the booking with the given ID."""

    booking = get_booking(
        booking_id=booking_id,
        database=database,
    )

    if booking is None:
        return None

    if booking.status == BookingStatus.CANCELLED:
        LOG_MSG.debug(
            f"Booking {booking.booking_id} is already cancelled.")
        return booking

    booking.status = BookingStatus.CANCELLED
    database.save_booking(booking)

    LOG_MSG.debug(
        f"Booking {booking.booking_id} was cancelled.")

    return booking