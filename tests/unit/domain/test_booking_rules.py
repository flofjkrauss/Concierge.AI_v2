"""Tests for room and booking-request matching rules."""

from datetime import date
from decimal import Decimal

import pytest

from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.rules.booking import room_matches_booking_request
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod


@pytest.fixture
def booking_request() -> BookingRequest:
    """Return a valid booking request for two guests."""

    return BookingRequest(
        request_id="request-001",
        stay_period=StayPeriod(
            check_in=date(2026, 10, 10),
            check_out=date(2026, 10, 13),
        ),
        guest_count=2,
    )


@pytest.fixture
def matching_room() -> Room:
    """Return a bookable room with sufficient capacity."""

    return Room(
        room_id="room-101",
        room_number="101",
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


def test_room_matches_booking_request(
    matching_room: Room,
    booking_request: BookingRequest,
) -> None:
    """A suitable and available room should match the request."""

    result = room_matches_booking_request(
        room=matching_room,
        booking_request=booking_request,
        existing_bookings=[],
    )

    assert result is True


def test_room_does_not_match_when_not_bookable(
    matching_room: Room,
    booking_request: BookingRequest,
) -> None:
    """A room that is out of service should not match."""

    matching_room.is_bookable = False

    result = room_matches_booking_request(
        room=matching_room,
        booking_request=booking_request,
        existing_bookings=[],
    )

    assert result is False


def test_room_does_not_match_when_capacity_is_too_low(
    matching_room: Room,
    booking_request: BookingRequest,
) -> None:
    """A room with insufficient capacity should not match."""

    matching_room.max_occupancy = 1

    result = room_matches_booking_request(
        room=matching_room,
        booking_request=booking_request,
        existing_bookings=[],
    )

    assert result is False


def test_room_does_not_match_when_already_booked(
    matching_room: Room,
    booking_request: BookingRequest,
) -> None:
    """A room blocked during the requested period should not match."""

    existing_booking = Booking(
        booking_id="booking-001",
        customer_id="customer-001",
        room_id=matching_room.room_id,
        stay_period=StayPeriod(
            check_in=date(2026, 10, 11),
            check_out=date(2026, 10, 14),
        ),
        guest_count=2,
        total_price=Money(
            amount=Decimal(300),
            currency="USD",
        ),
        status=BookingStatus.CONFIRMED,
    )

    result = room_matches_booking_request(
        room=matching_room,
        booking_request=booking_request,
        existing_bookings=[existing_booking],
    )

    assert result is False

def test_cancelled_booking_does_not_block_room(
    matching_room: Room,
    booking_request: BookingRequest,
) -> None:
    """A cancelled booking should not prevent a room match."""

    cancelled_booking = Booking(
        booking_id="booking-001",
        customer_id="customer-001",
        room_id=matching_room.room_id,
        stay_period=StayPeriod(
            check_in=date(2026, 10, 11),
            check_out=date(2026, 10, 14),
        ),
        guest_count=2,
        total_price=Money(
            amount=Decimal(300),
            currency="USD",
        ),
        status=BookingStatus.CANCELLED,
    )

    result = room_matches_booking_request(
        room=matching_room,
        booking_request=booking_request,
        existing_bookings=[cancelled_booking],
    )

    assert result is True