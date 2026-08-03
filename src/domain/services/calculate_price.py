"""Service for calculating the price of a booking request."""

from database.interface import DatabaseInterface
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.value_objects.money import Money


def calculate_price(
    booking_request: BookingRequest,
    room: Room,
    database: DatabaseInterface,
) -> Money:
    """Calculate the total price for a booking request and room."""

    price_per_night = room.price_per_night

    if booking_request.breakfast_included:
        breakfast_price = database.get_breakfast_price()

        price_per_night = (
            price_per_night
            + breakfast_price * booking_request.guest_count
        )

    return price_per_night * booking_request.stay_period.number_of_nights