from dataclasses import replace

from conftest import InMemoryDatabase

from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.services.find_matching_rooms import find_matching_rooms


def test_find_matching_rooms_filters_inventory(
    room: Room,
    booking: Booking,
    booking_request: BookingRequest,
    database: InMemoryDatabase,
) -> None:
    available = replace(room, room_id="room-available", room_number="102")
    database.rooms.extend([room, available, replace(room, room_id="closed", is_bookable=False)])
    database.bookings.append(booking)

    assert find_matching_rooms(booking_request, database) == [available]


def test_find_matching_rooms_returns_empty_list_without_matches(
    booking_request: BookingRequest,
    database: InMemoryDatabase,
) -> None:
    assert find_matching_rooms(booking_request, database) == []
