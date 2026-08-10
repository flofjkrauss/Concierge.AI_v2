from unittest.mock import Mock

from conftest import InMemoryDatabase

from api.routers.availability import read_availability
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.services.find_matching_rooms import MatchResponse


def test_read_availability_maps_matching_rooms(
    monkeypatch, booking_request: BookingRequest, room: Room, database: InMemoryDatabase
) -> None:
    find_rooms = Mock(return_value=MatchResponse(booking_request, [room]))
    monkeypatch.setattr("api.routers.availability.find_matching_rooms", find_rooms)

    response = read_availability(
        database=database,
        check_in=str(booking_request.stay_period.check_in),
        check_out=str(booking_request.stay_period.check_out),
        guest_count=booking_request.guest_count,
        breakfast=booking_request.breakfast_included,
        accessible=booking_request.accessible_requested,
    )

    find_rooms.assert_called_once_with(
        check_in=booking_request.stay_period.check_in,
        check_out=booking_request.stay_period.check_out,
        guest_count=booking_request.guest_count,
        breakfast=booking_request.breakfast_included,
        accessible=booking_request.accessible_requested,
        database=database,
    )
    assert len(response.rooms) == 1
    assert response.rooms[0].category == room.category
    assert response.rooms[0].max_occupancy == room.max_occupancy
    assert response.rooms[0].price_per_night == room.price_per_night


def test_read_availability_returns_empty_rooms(
    monkeypatch, booking_request: BookingRequest, database: InMemoryDatabase
) -> None:
    monkeypatch.setattr(
        "api.routers.availability.find_matching_rooms",
        Mock(return_value=MatchResponse(booking_request, [])),
    )

    response = read_availability(
        database=database,
        check_in=str(booking_request.stay_period.check_in),
        check_out=str(booking_request.stay_period.check_out),
        guest_count=booking_request.guest_count,
        breakfast=booking_request.breakfast_included,
        accessible=booking_request.accessible_requested,
    )

    assert response.rooms == []


def test_read_availability_rejects_invalid_date(
    monkeypatch,
    database: InMemoryDatabase,
) -> None:
    find_rooms = Mock()
    monkeypatch.setattr("api.routers.availability.find_matching_rooms", find_rooms)

    response = read_availability(
        database=database,
        check_in="not-a-date",
        check_out="2030-06-13",
        guest_count=2,
        breakfast=False,
        accessible=False,
    )

    assert response.rooms == []
    find_rooms.assert_not_called()
