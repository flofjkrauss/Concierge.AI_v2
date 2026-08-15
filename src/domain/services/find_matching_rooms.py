"""Service for finding rooms that match a booking request."""
from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from database.interface import DatabaseInterface
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.rules.booking import room_matches_booking_request
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod
from observability.log_messages import LOG_MSG
from observability.utils.to_json import to_jsonable


@dataclass(slots=True)
class MatchResponse:
    request: BookingRequest | None
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
    retval = MatchResponse(
        request=None,
        rooms=[]
    )
    if not all([
        isinstance(check_in, date),
        isinstance(check_out, date),
        isinstance(guest_count, int),
        isinstance(breakfast, bool),
        isinstance(accessible, bool)
    ]):
        LOG_MSG.error("Invalid data in find_matching_rooms")
        return retval

    try:    
        booking_request = BookingRequest(
            request_id=str(uuid4()),
            stay_period=StayPeriod(check_in, check_out),
            guest_count=guest_count,
            breakfast_included=breakfast,
            accessible_requested=accessible
        )
        retval.request = booking_request
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
            f"Found {len(matching_rooms)} matching rooms for booking request {booking_request.request_id}.", 
            extra=to_jsonable(booking_request)
        )
        retval.rooms = matching_rooms

    except (KeyError, ValueError, TypeError) as error:
        LOG_MSG.error(f"find_matching_room failed due to an exception: {error}")

    return retval
