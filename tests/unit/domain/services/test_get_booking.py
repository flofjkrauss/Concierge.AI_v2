from datetime import date

import pytest
from conftest import InMemoryDatabase

from domain.entities.booking import Booking
from domain.entities.customer import Customer
from domain.services.get_booking import get_booking, get_booking_by_name


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


def test_get_booking_by_name_returns_database_result(
    booking: Booking,
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    database.customers.append(customer)
    database.bookings.append(booking)

    result = get_booking_by_name(
        customer.last_name,
        customer.email,
        booking.stay_period.check_in,
        database,
    )

    assert result is booking


@pytest.mark.parametrize(
    ("last_name", "email", "expected_message"),
    [
        ("", "alex@example.com", "last_name must not be empty"),
        ("Morgan", "", "email must not be empty"),
    ],
)
def test_get_booking_by_name_rejects_missing_identity(
    last_name: str,
    email: str,
    expected_message: str,
    database: InMemoryDatabase,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        get_booking_by_name(
            last_name,
            email,
            date(2030, 6, 10),
            database,
        )


def test_get_booking_by_name_requires_date(database: InMemoryDatabase) -> None:
    with pytest.raises(TypeError, match="check_in must be a date object"):
        get_booking_by_name(
            "Morgan",
            "alex@example.com",
            "2030-06-10",  # type: ignore[arg-type]
            database,
        )
