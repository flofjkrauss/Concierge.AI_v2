"""Service for confirming a booking request."""


from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.customer import Customer
from domain.entities.room import Room
from domain.rules.booking import room_matches_booking_request
from domain.services.calculate_price import calculate_price
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.room_category import RoomCategory
from observability import LOG_MSG


def confirm_booking(
    booking_request: BookingRequest,
    room_category: RoomCategory,
    customer: Customer,
    database: DatabaseInterface,
) -> Booking:
    """Create and persist a confirmed booking."""

    existing_bookings = database.get_bookings()
    matching_room: Room
    for room in database.get_rooms():
        if not room_matches_booking_request(
            room=room,
            category=room_category,
            booking_request=booking_request,
            existing_bookings=existing_bookings,
        ):
            continue
        else:
            matching_room = room
            break
    else:
        raise ValueError(
            f"Room category {room_category} is no longer available for booking request {booking_request.request_id}"
        )

    if customer is None:
        raise ValueError(
            "No customer data available. Pleas create customer entry before booking confirmation."
        )

    total_price = calculate_price(
        booking_request=booking_request,
        room=matching_room,
        database=database,
    )


    booking = Booking(
        booking_id=booking_request.request_id,
        customer_id=customer.customer_id,
        room_id=matching_room.room_id,
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

def get_room(room_id: str, database: DatabaseInterface) -> Room | None:
    return database.get_room(room_id=room_id)