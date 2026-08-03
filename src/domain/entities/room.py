"""Room domain entity."""

from dataclasses import dataclass

from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory


@dataclass(slots=True)
class Room:
    """A bookable hotel room."""

    room_id: str
    room_number: str
    floor: int
    category: RoomCategory
    max_occupancy: int
    price_per_night: Money
    is_accessible: bool
    is_bookable: bool = True

    def __post_init__(self) -> None:
        if not self.room_id.strip():
            raise ValueError("room_id must not be empty")

        if not self.room_number.strip():
            raise ValueError("room_number must not be empty")

        if not self.category.strip():
            raise ValueError("category must not be empty")

        if self.max_occupancy < 1:
            raise ValueError("max_occupancy must be at least 1")

    def can_accommodate(self, guest_count: int) -> bool:
        """Return whether the room can accommodate the requested guests."""

        if guest_count < 1:
            raise ValueError("guest_count must be at least 1")

        return self.is_bookable and guest_count <= self.max_occupancy