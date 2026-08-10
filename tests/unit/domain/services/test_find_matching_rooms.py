from dataclasses import replace

from conftest import InMemoryDatabase

from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.services.find_matching_rooms import find_matching_rooms
from domain.value_objects.room_category import RoomCategory


def test_find_matching_rooms_filters_inventory(
    room: Room,
    booking: Booking,
    booking_request: BookingRequest,
    database: InMemoryDatabase,
) -> None:
    available = replace(room, room_id="room-available", room_number="102")
    database.rooms.extend(
        [room, available, replace(room, room_id="closed", is_bookable=False)]
    )
    database.bookings.append(booking)

    result = find_matching_rooms(
        check_in=booking_request.stay_period.check_in,
        check_out=booking_request.stay_period.check_out,
        guest_count=booking_request.guest_count,
        breakfast=booking_request.breakfast_included,
        accessible=booking_request.accessible_requested,
        database=database,
    )

    assert result is not None
    assert result.request.stay_period == booking_request.stay_period
    assert result.rooms == [available]


def test_find_matching_rooms_returns_empty_list_without_matches(
    booking_request: BookingRequest,
    database: InMemoryDatabase,
) -> None:
    result = find_matching_rooms(
        check_in=booking_request.stay_period.check_in,
        check_out=booking_request.stay_period.check_out,
        guest_count=booking_request.guest_count,
        breakfast=booking_request.breakfast_included,
        accessible=booking_request.accessible_requested,
        database=database,
    )

    assert result is not None
    assert result.rooms == []


def test_find_matching_rooms_filters_requested_category(
    room: Room,
    booking_request: BookingRequest,
    database: InMemoryDatabase,
) -> None:
    database.rooms.append(room)

    result = find_matching_rooms(
        check_in=booking_request.stay_period.check_in,
        check_out=booking_request.stay_period.check_out,
        guest_count=booking_request.guest_count,
        breakfast=booking_request.breakfast_included,
        accessible=booking_request.accessible_requested,
        database=database,
        room_category=RoomCategory.FAMILY,
    )

    assert result is not None
    assert result.rooms == []
