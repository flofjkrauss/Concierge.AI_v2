"""Service for finding rooms that match a booking request."""

from database.interface import DatabaseInterface
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.rules.booking import room_matches_booking_request
from observability import LOG_MSG


def find_matching_rooms(
    booking_request: BookingRequest,
    database: DatabaseInterface,
) -> list[Room]:
    """Return all rooms that satisfy the given booking request."""

    rooms = database.get_rooms()
    existing_bookings = database.get_bookings()

    matching_rooms = [
        room
        for room in rooms
        if room_matches_booking_request(
            room=room,
            booking_request=booking_request,
            existing_bookings=existing_bookings,
        )
    ]

    LOG_MSG.debug(
        f"Found {len(matching_rooms)} matching rooms for booking request {booking_request.request_id}.")

    return matching_rooms