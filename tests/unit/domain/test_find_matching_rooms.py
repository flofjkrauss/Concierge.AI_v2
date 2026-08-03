"""Tests for the find-matching-rooms service."""

from datetime import date
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from database.interface import DatabaseInterface
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.services.find_matching_rooms import find_matching_rooms
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod


@pytest.fixture
def booking_request() -> BookingRequest:
    """Return a valid booking request."""

    return BookingRequest(
        request_id="request-001",
        stay_period=StayPeriod(
            check_in=date(2026, 10, 10),
            check_out=date(2026, 10, 13),
        ),
        guest_count=2,
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


def test_find_matching_rooms_returns_matching_rooms(
    booking_request: BookingRequest,
) -> None:
    """The service should return rooms that can fulfil the request."""

    matching_room = _create_room("room-101")
    insufficient_room = _create_room(
        "room-107",
        max_occupancy=1,
    )

    database = create_autospec(
        DatabaseInterface,
        instance=True,
    )
    database.get_rooms.return_value = [
        matching_room,
        insufficient_room,
    ]
    database.get_bookings.return_value = []

    result = find_matching_rooms(
        booking_request=booking_request,
        database=database,
    )

    assert result == [matching_room]

    database.get_rooms.assert_called_once_with()
    database.get_bookings.assert_called_once_with()


def test_find_matching_rooms_returns_empty_list_when_request_cannot_be_served(
    booking_request: BookingRequest,
) -> None:
    """The service should return no rooms when none fulfil the request."""

    unavailable_room = _create_room(
        "room-101",
        is_bookable=False,
    )
    insufficient_room = _create_room(
        "room-107",
        max_occupancy=1,
    )

    database = create_autospec(
        DatabaseInterface,
        instance=True,
    )
    database.get_rooms.return_value = [
        unavailable_room,
        insufficient_room,
    ]
    database.get_bookings.return_value = []

    result = find_matching_rooms(
        booking_request=booking_request,
        database=database,
    )

    assert result == []