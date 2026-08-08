"""Service for finding rooms that match a booking request."""
from datetime import date
from uuid import uuid4
from dataclasses import dataclass

from database.interface import DatabaseInterface
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.rules.booking import room_matches_booking_request
from domain.value_objects.stay_period import StayPeriod
from domain.value_objects.room_category import RoomCategory
from observability import LOG_MSG

@dataclass(slots=True, frozen=True)
class MatchResponse:
    request: BookingRequest
    rooms: list[Room]

def find_matching_rooms(
    check_in: date,
    check_out: date,
    guest_count: int,
    breakfast: bool,
    accessible: bool,
    database: DatabaseInterface,
    room_category: RoomCategory = ""
) -> MatchResponse:
    """Return all rooms that satisfy the given booking request."""
    if not all([
        isinstance(check_in, date),
        isinstance(check_out, date),
        isinstance(guest_count, int),
        isinstance(breakfast, bool),
        isinstance(accessible, bool)
    ]):
        LOG_MSG.error("Invalid data in find_matching_rooms")
        return []
    
    booking_request = BookingRequest(
        request_id=str(uuid4()),
        stay_period=StayPeriod(check_in, check_out),
        guest_count=guest_count,
        breakfast_included=breakfast,
        accessible_requested=accessible
    )
    LOG_MSG.debug(f"Incoming request {booking_request}")
    rooms = database.get_rooms()
    existing_bookings = database.get_bookings()

    matching_rooms = [
        room
        for room in rooms
        if room_matches_booking_request(
            room=room,
            category=room_category,
            booking_request=booking_request,
            existing_bookings=existing_bookings,
        )
    ]

    LOG_MSG.debug(
        f"Found {len(matching_rooms)} matching rooms for booking request {booking_request.request_id}.")

    return MatchResponse(
        request=booking_request,
        rooms=matching_rooms
    )