import pytest
from conftest import InMemoryDatabase

from domain.entities.booking import Booking
from domain.services.get_booking import get_booking


def test_get_booking_returns_database_result(
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    database.bookings.append(booking)

    assert get_booking("booking-1", database) is booking


def test_get_booking_returns_none_when_missing(database: InMemoryDatabase) -> None:
    assert get_booking("missing", database) is None


def test_get_booking_rejects_blank_id(database: InMemoryDatabase) -> None:
    with pytest.raises(ValueError, match="booking_id must not be empty"):
        get_booking("  ", database)
