from dataclasses import replace
from datetime import date

from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.rules.booking import room_matches_booking_request
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod


def test_matching_room_is_available(
    room: Room,
    booking_request: BookingRequest,
) -> None:
    assert room_matches_booking_request(room, "", booking_request, [])


def test_unbookable_room_does_not_match(
    room: Room,
    booking_request: BookingRequest,
) -> None:
    assert not room_matches_booking_request(
        replace(room, is_bookable=False),
        "",
        booking_request,
        [],
    )


def test_room_below_requested_capacity_does_not_match(
    room: Room,
    booking_request: BookingRequest,
) -> None:
    assert not room_matches_booking_request(
        replace(room, max_occupancy=1),
        "",
        booking_request,
        [],
    )


def test_non_accessible_room_does_not_match_accessible_request(
    room: Room,
    booking_request: BookingRequest,
) -> None:
    assert not room_matches_booking_request(
        replace(room, is_accessible=False),
        "",
        replace(booking_request, accessible_requested=True),
        [],
    )


def test_overlapping_confirmed_booking_blocks_same_room(
    room: Room,
    booking_request: BookingRequest,
    booking: Booking,
) -> None:
    assert not room_matches_booking_request(room, "", booking_request, [booking])


def test_cancelled_booking_does_not_block_room(
    room: Room,
    booking_request: BookingRequest,
    booking: Booking,
) -> None:
    booking.status = BookingStatus.CANCELLED

    assert room_matches_booking_request(room, "", booking_request, [booking])


def test_booking_for_other_room_does_not_block_room(
    room: Room,
    booking_request: BookingRequest,
    booking: Booking,
) -> None:
    booking.room_id = "room-999"

    assert room_matches_booking_request(room, "", booking_request, [booking])


def test_adjacent_booking_does_not_block_room(
    room: Room,
    booking_request: BookingRequest,
    booking: Booking,
) -> None:
    booking.stay_period = StayPeriod(
        date(2030, 6, 7),
        booking_request.stay_period.check_in,
    )

    assert room_matches_booking_request(room, "", booking_request, [booking])


def test_room_with_different_category_does_not_match(
    room: Room,
    booking_request: BookingRequest,
) -> None:
    assert not room_matches_booking_request(
        room,
        RoomCategory.FAMILY,
        booking_request,
        [],
    )
