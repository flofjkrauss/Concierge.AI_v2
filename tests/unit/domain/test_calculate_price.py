"""Tests for the calculate-price service."""

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
    breakfast_included: bool,
) -> BookingRequest:
    """Return a valid booking request for two guests and three nights."""

    return BookingRequest(
        request_id="request-001",
        stay_period=StayPeriod(
            check_in=date(2026, 10, 10),
            check_out=date(2026, 10, 13),
        ),
        guest_count=2,
        breakfast_included=breakfast_included,
    )


def _create_room() -> Room:
    """Return a valid room for price calculation."""

    return Room(
        room_id="room-107",
        room_number="107",
        floor=1,
        category=RoomCategory.DOUBLE,
        max_occupancy=2,
        price_per_night=Money(
            amount=Decimal(100),
            currency="USD",
        ),
        is_accessible=False,
        is_bookable=True,
    )


def test_calculate_price_without_breakfast() -> None:
    """Return only the room price when breakfast is not requested."""

    booking_request = _create_booking_request(
        breakfast_included=False,
    )
    room = _create_room()

    database = create_autospec(
        DatabaseInterface,
        instance=True,
    )

    result = calculate_price(
        booking_request=booking_request,
        room=room,
        database=database,
    )

    assert result == Money(
        amount=Decimal(300),
        currency="USD",
    )
    database.get_breakfast_price.assert_not_called()


def test_calculate_price_with_breakfast() -> None:
    """Add breakfast per guest and night when requested."""

    booking_request = _create_booking_request(
        breakfast_included=True,
    )
    room = _create_room()

    database = create_autospec(
        DatabaseInterface,
        instance=True,
    )
    database.get_breakfast_price.return_value = Money(
        amount=Decimal(20),
        currency="USD",
    )

    result = calculate_price(
        booking_request=booking_request,
        room=room,
        database=database,
    )

    assert result == Money(
        amount=Decimal(420),
        currency="USD",
    )
    database.get_breakfast_price.assert_called_once_with()