"""Service for confirming a booking request."""

from uuid import uuid4

from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.customer import Customer
from domain.entities.room import Room
from domain.rules.booking import room_matches_booking_request
from domain.services.calculate_price import calculate_price
from domain.value_objects.booking_status import BookingStatus
from observability import LOG_MSG


def confirm_booking(
    booking_request: BookingRequest,
    room: Room,
    customer: Customer,
    database: DatabaseInterface,
) -> Booking:
    """Create and persist a confirmed booking."""

    existing_bookings = database.get_bookings()

    if not room_matches_booking_request(
        room=room,
        booking_request=booking_request,
        existing_bookings=existing_bookings,
    ):
        raise ValueError(
            f"Room {room.room_id} is no longer available for booking request {booking_request.request_id}"
        )

    if customer is None:
        raise ValueError(
            "No customer data available. Pleas create customer entry before booking confirmation."
        )

    total_price = calculate_price(
        booking_request=booking_request,
        room=room,
        database=database,
    )

    booking = Booking(
        booking_id=str(uuid4()),
        customer_id=customer.customer_id,
        room_id=room.room_id,
        stay_period=booking_request.stay_period,
        guest_count=booking_request.guest_count,
        total_price=total_price,
        status=BookingStatus.CONFIRMED,
        breakfast_included=booking_request.breakfast_included,
        accessible_requested=booking_request.accessible_requested,
    )

    database.save_booking(booking)

    LOG_MSG.debug(
        f"Booking {booking.booking_id} was confirmed from booking request {booking_request.request_id} for room {room.room_id} and customer {customer.customer_id}.")

    return booking