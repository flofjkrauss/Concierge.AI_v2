"""Business rules for matching rooms to bookings."""

from collections.abc import Collection

from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from observability import LOG_MSG


def room_matches_booking_request(
    room: Room,
    booking_request: BookingRequest,
    existing_bookings: Collection[Booking],
) -> bool:
    """Return whether a room satisfies all requirements of a booking request."""

    if not room.is_bookable:
        LOG_MSG.debug(
            f"Room {room.room_id} does not match booking request {booking_request.request_id} because the room is not bookable.")
        return False

    if room.max_occupancy < booking_request.guest_count:
        LOG_MSG.debug(
            f"Room {room.room_id} does not match booking request {booking_request.request_id}, because its maximum occupancy is {room.max_occupancy} persons, but {booking_request.guest_count} persons have been requested.")
        return False

    if booking_request.accessible_requested and not room.is_accessible:
        LOG_MSG.debug(
            f"Room {room.room_id} does not match booking request {booking_request.request_id}, because the room is not accessible, but accessability has been requested.")
        return False

    conflicting_booking = _find_conflicting_booking(
        room=room,
        booking_request=booking_request,
        existing_bookings=existing_bookings,
    )

    if conflicting_booking is not None:
        LOG_MSG.debug(
            f"Room {room.room_id} does not match booking request {booking_request.request_id}, because it is already blocked by booking {conflicting_booking.booking_id}.")
        return False

    return True


def _find_conflicting_booking(
    room: Room,
    booking_request: BookingRequest,
    existing_bookings: Collection[Booking],
) -> Booking | None:
    """Return the first existing booking that blocks the requested room."""
    for existing_booking in existing_bookings:
        if existing_booking.room_id != room.room_id:
            continue

        periods_overlap = existing_booking.stay_period.overlaps(
            booking_request.stay_period
        )

        if periods_overlap and existing_booking.status.blocks_room:
            return existing_booking

    return None