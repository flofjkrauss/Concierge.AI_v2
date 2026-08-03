"""Tests for the find-matching-rooms service."""

from datetime import date
from decimal import Decimal
from unittest.mock import create_autospec

from database.interface import DatabaseInterface
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.services.calculate_price import calculate_price
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod


def _create_booking_request(
        *,
        breakfast_included: bool
) -> BookingRequest:
    """Return a valid booking request."""

    return BookingRequest(
        # 3 nights stay period
        request_id="request-001",
        stay_period=StayPeriod(
            check_in=date(2026, 10, 10),
            check_out=date(2026, 10, 13),
        ),
        guest_count=2,
        breakfast_included=breakfast_included
    )


def _create_room(
    room_id: str,
    *,
    max_occupancy: int = 2,
    is_bookable: bool = True,
) -> Room:
    """Create a room for service tests."""

    return Room(
        room_id=room_id,
        room_number=room_id.removeprefix("room-"),
        floor=1,
        category=RoomCategory.DOUBLE,
        max_occupancy=max_occupancy,
        price_per_night=Money(
            amount=Decimal(100),
            currency="USD",
        ),
        is_accessible=False,
        is_bookable=is_bookable,
    )


def test_calculate_price_without_breakfast(
) -> None:
    """The service should return rooms that can fulfil the request."""

    booking_request = _create_booking_request(
        breakfast_included=False
    )

    room = _create_room(
        "room-107",
        max_occupancy=1,
    )

    database = create_autospec(
        DatabaseInterface,
        instance=True,
    )

    database.get_breakfast_price.return_value = Money(Decimal(20), "USD")

    result = calculate_price(
        booking_request=booking_request,
        room=room,
        database=database,
    )
    # 3 nights stay a 100 USD = 300 USD

    assert result == Money(Decimal(300), "USD")



def test_calculate_price_with_breakfast(
) -> None:
    """The service should return rooms that can fulfil the request."""

    booking_request = _create_booking_request(
        breakfast_included=True
    )

    room = _create_room(
        "room-107",
        max_occupancy=1,
    )

    database = create_autospec(
        DatabaseInterface,
        instance=True,
    )

    database.get_breakfast_price.return_value = Money(Decimal(20), "USD")

    result = calculate_price(
        booking_request=booking_request,
        room=room,
        database=database,
    )
    # 3 nights stay a 100 USD = 300 USD

    assert result == Money(Decimal(420), "USD")