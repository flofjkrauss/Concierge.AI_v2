from dataclasses import replace
from decimal import Decimal

from conftest import InMemoryDatabase

from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.services.calculate_price import calculate_price
from domain.value_objects.money import Money


def test_calculate_price_uses_room_rate_and_number_of_nights(
    booking_request: BookingRequest,
    room: Room,
    database: InMemoryDatabase,
) -> None:
    assert calculate_price(booking_request, room, database) == Money(
        Decimal("300.00"),
        "EUR",
    )


def test_calculate_price_adds_breakfast_per_guest_and_night(
    booking_request: BookingRequest,
    room: Room,
    database: InMemoryDatabase,
) -> None:
    request_with_breakfast = replace(booking_request, breakfast_included=True)

    assert calculate_price(request_with_breakfast, room, database) == Money(
        Decimal("375.00"),
        "EUR",
    )
