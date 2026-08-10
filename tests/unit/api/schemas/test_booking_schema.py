from datetime import date
from decimal import Decimal

from api.schemas.booking_schema import BookingResponse
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory


def test_booking_response_keeps_confirmation_fields() -> None:
    response = BookingResponse(
        booking_id="booking-1",
        room_category=RoomCategory.DOUBLE,
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
    assert response.room_category is RoomCategory.DOUBLE
    assert response.total_price == Money(Decimal("405.00"), "EUR")
    assert response.status == "confirmed"
