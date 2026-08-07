from unittest.mock import Mock

from conftest import InMemoryDatabase

from api.routers.availability import read_availability
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room


def test_read_availability_maps_matching_rooms(monkeypatch, booking_request: BookingRequest, room: Room, database: InMemoryDatabase) -> None:
    find_rooms = Mock(return_value=[room])
    monkeypatch.setattr("api.routers.availability.find_matching_rooms", find_rooms)

    response = read_availability(booking_request, database)

    find_rooms.assert_called_once_with(
        booking_request=booking_request,
        database=database,
    )
    assert response.request_id == booking_request.request_id
    assert len(response.rooms) == 1
    assert response.rooms[0].room_id == room.room_id
    assert response.rooms[0].category == room.category
    assert response.rooms[0].price_per_night == room.price_per_night


def test_read_availability_returns_empty_rooms(monkeypatch, booking_request: BookingRequest, database: InMemoryDatabase) -> None:
    monkeypatch.setattr(
        "api.routers.availability.find_matching_rooms",
        Mock(return_value=[]),
    )

    assert read_availability(booking_request, database).rooms == []
