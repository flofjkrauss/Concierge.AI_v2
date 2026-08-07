from datetime import date
from decimal import Decimal

from api.schemas.availability_schema import AvailabilityResponse, RoomResponse
from api.schemas.booking_schema import BookingResponse
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory


def test_availability_schema_serializes_room_values() -> None:
    response = AvailabilityResponse(
        request_id="request-1",
        rooms=[
            RoomResponse(
                room_id="room-1",
                category=RoomCategory.DOUBLE,
                max_occupancy=2,
                price_per_night=Money(Decimal("120.00"), "EUR"),
            )
        ],
    )

    assert response.rooms[0].category == "double"
    assert response.model_dump()["rooms"][0]["price_per_night"] == {
        "amount": Decimal("120.00"),
        "currency": "EUR",
    }


def test_booking_schema_keeps_confirmation_fields() -> None:
    response = BookingResponse(
        booking_id="booking-1",
        customer_id="customer-1",
        guest_name="Alex Morgan",
        arrival=date(2030, 6, 10),
        departure=date(2030, 6, 13),
        guests=2,
        breakfast=True,
        total_price=Money(Decimal("405.00"), "EUR"),
        hotel_name="Harbour Light Hotel",
        hotel_address="1 Harbour Way",
        status="confirmed",
    )

    assert response.arrival == date(2030, 6, 10)
    assert response.total_price == Money(Decimal("405.00"), "EUR")
    assert response.status == "confirmed"
