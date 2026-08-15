from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from domain.entities.room import Room
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory


class RoomResponse(BaseModel):
    category: RoomCategory
    max_occupancy: int
    price_per_night: Money


class AvailabilityRequestResponse(BaseModel):
    """Search criteria needed to turn one room option into a booking request."""

    check_in: date
    check_out: date
    guest_count: int
    accessible: bool


class AvailabilityResponse(BaseModel):
    """A Harbour Light Hotel availability response."""

    rooms: list[RoomResponse] = Field(default_factory=list)
    request: AvailabilityRequestResponse | None = None

    def add_room(self, room: Room) -> None:
        for listed_room in self.rooms:
            if all(
                [
                    listed_room.category == room.category,
                    listed_room.max_occupancy == room.max_occupancy,
                    listed_room.price_per_night == room.price_per_night,
                ]
            ):
                return
        self.rooms.append(
            RoomResponse(
                category=room.category,
                max_occupancy=room.max_occupancy,
                price_per_night=room.price_per_night,
            )
        )
