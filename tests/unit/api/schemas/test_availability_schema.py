from dataclasses import replace
from decimal import Decimal

from api.schemas.availability_schema import AvailabilityResponse, RoomResponse
from domain.entities.room import Room
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory


def test_availability_response_serializes_room_values() -> None:
    response = AvailabilityResponse(
        rooms=[
            RoomResponse(
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


def test_add_room_collapses_equivalent_room_options(room: Room) -> None:
    response = AvailabilityResponse()

    response.add_room(room)
    response.add_room(replace(room, room_id="room-102", room_number="102"))

    assert len(response.rooms) == 1
    assert response.rooms[0].category == room.category
    assert response.rooms[0].max_occupancy == room.max_occupancy
    assert response.rooms[0].price_per_night == room.price_per_night


def test_room_responses_are_not_shared_between_instances(room: Room) -> None:
    first = AvailabilityResponse()
    second = AvailabilityResponse()

    first.add_room(room)

    assert len(first.rooms) == 1
    assert second.rooms == []
