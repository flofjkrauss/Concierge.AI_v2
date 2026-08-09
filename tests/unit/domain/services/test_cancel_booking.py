from conftest import InMemoryDatabase

from domain.entities.booking import Booking
from domain.services.cancel_booking import cancel_booking
from domain.value_objects.booking_status import BookingStatus


def test_cancel_booking_updates_status_and_persists(
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    database.bookings.append(booking)

    result = cancel_booking("booking-1", database)

    assert result is booking
    assert booking.status is BookingStatus.CANCELLED
    assert database.saved_bookings == [booking]


def test_cancel_booking_is_idempotent_for_cancelled_booking(
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    booking.status = BookingStatus.CANCELLED
    database.bookings.append(booking)

    assert cancel_booking("booking-1", database) is booking
    assert database.saved_bookings == []


def test_cancel_booking_returns_none_when_not_found(
    database: InMemoryDatabase,
) -> None:
    assert cancel_booking("missing", database) is None
    assert database.saved_bookings == []
