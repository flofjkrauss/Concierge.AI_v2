from decimal import Decimal

import pytest
from conftest import InMemoryDatabase

from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.customer import Customer
from domain.entities.room import Room
from domain.services.confirm_booking import confirm_booking, get_room
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.money import Money


def test_confirm_booking_creates_and_persists_confirmed_booking(
    booking_request: BookingRequest,
    room: Room,
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    database.rooms.append(room)
    database.customers.append(customer)

    result = confirm_booking(booking_request, room.category, customer, database)

    assert result.status is BookingStatus.CONFIRMED
    assert result.customer_id == customer.customer_id
    assert result.room_id == room.room_id
    assert result.total_price == Money(Decimal("300.00"), "EUR")
    assert database.saved_bookings == [result]


def test_confirm_booking_rechecks_room_availability(
    booking_request: BookingRequest,
    room: Room,
    customer: Customer,
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    database.rooms.append(room)
    database.bookings.append(booking)

    with pytest.raises(ValueError, match="no longer available"):
        confirm_booking(booking_request, room.category, customer, database)

    assert database.saved_bookings == []


def test_confirm_booking_requires_customer_after_availability_check(
    booking_request: BookingRequest,
    room: Room,
    database: InMemoryDatabase,
) -> None:
    database.rooms.append(room)

    with pytest.raises(ValueError, match="No customer data available"):
        confirm_booking(
            booking_request,
            room.category,
            None,  # type: ignore[arg-type]
            database,
        )


def test_get_room_delegates_to_database(
    room: Room,
    database: InMemoryDatabase,
) -> None:
    database.rooms.append(room)

    assert get_room(room.room_id, database) is room
