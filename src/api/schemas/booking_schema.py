from datetime import date

from pydantic import BaseModel

from domain.value_objects.money import Money


class BookingResponse(BaseModel):
    """A Harbour Light Hotel booking confirmation."""

    booking_id: str
    customer_id: str
    guest_name: str
    arrival: date
    departure: date
    guests: int
    breakfast: bool
    total_price: Money
    hotel_name: str
    hotel_address: str
    status: str
