from decimal import Decimal

import pytest

from domain.entities.room import Room
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory


def make_room(**changes: object) -> Room:
    values = {
        "room_id": "room-1",
        "room_number": "101",
        "floor": 1,
        "category": RoomCategory.DOUBLE,
        "max_occupancy": 2,
        "price_per_night": Money(Decimal("100.00"), "EUR"),
        "is_accessible": False,
        "is_bookable": True,
    }
    values.update(changes)
    return Room(**values)  # type: ignore[arg-type]


def test_room_can_accommodate_within_capacity() -> None:
    assert make_room().can_accommodate(2)


def test_unbookable_room_cannot_accommodate_guests() -> None:
    assert not make_room(is_bookable=False).can_accommodate(1)


def test_room_cannot_accommodate_above_capacity() -> None:
    assert not make_room().can_accommodate(3)


def test_room_rejects_non_positive_requested_guest_count() -> None:
    with pytest.raises(ValueError, match="guest_count must be at least 1"):
        make_room().can_accommodate(0)


@pytest.mark.parametrize("field", ["room_id", "room_number"])
def test_room_rejects_blank_identifiers(field: str) -> None:
    with pytest.raises(ValueError, match=f"{field} must not be empty"):
        make_room(**{field: " "})


def test_room_requires_positive_capacity() -> None:
    with pytest.raises(ValueError, match="max_occupancy must be at least 1"):
        make_room(max_occupancy=0)


def test_room_rejects_blank_category() -> None:
    with pytest.raises(ValueError, match="category must not be empty"):
        make_room(category=" ")
