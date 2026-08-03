from __future__ import annotations

from pydantic import BaseModel

from domain.value_objects.money import Money


class AvailabilityResponse(BaseModel):
    """A Harbour Light Hotel availability response."""

    request_id: str
    rooms: list[RoomResponse]

class RoomResponse(BaseModel):
    room_id: str
    category: str
    max_occupancy: int
    price_per_night: Money
