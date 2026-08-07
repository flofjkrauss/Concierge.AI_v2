from unittest.mock import Mock

import pytest
from conftest import InMemoryDatabase
from fastapi import HTTPException

from api.routers.bookings import (
    _response_from_booking,
    read_booking,
    read_booking_request,
    read_booking_to_cancel,
)
from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.customer import Customer
from domain.entities.room import Room


def test_read_booking_maps_service_result(
    monkeypatch,
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    get_booking = Mock(return_value=booking)
    response_from_booking = Mock(return_value="response")
    monkeypatch.setattr("api.routers.bookings.get_booking", get_booking)
    monkeypatch.setattr(
        "api.routers.bookings._response_from_booking",
        response_from_booking,
    )

    assert read_booking("booking-1", database) == "response"
    get_booking.assert_called_once_with(booking_id="booking-1", database=database)
    response_from_booking.assert_called_once_with(booking=booking, database=database)


def test_read_booking_to_cancel_maps_service_result(
    monkeypatch,
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    cancel = Mock(return_value=booking)
    response_from_booking = Mock(return_value="response")
    monkeypatch.setattr("api.routers.bookings.cancel_booking", cancel)
    monkeypatch.setattr(
        "api.routers.bookings._response_from_booking",
        response_from_booking,
    )

    assert read_booking_to_cancel("booking-1", database) == "response"
    cancel.assert_called_once_with(booking_id="booking-1", database=database)


def test_read_booking_request_returns_404_when_room_is_missing(
    monkeypatch,
    booking_request: BookingRequest,
    database: InMemoryDatabase,
) -> None:
    monkeypatch.setattr("api.routers.bookings.get_room", Mock(return_value=None))

    with pytest.raises(HTTPException) as error:
        read_booking_request(
            booking_request,
            "missing",
            "Alex",
            "Morgan",
            "alex@example.com",
            "en",
            database,
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Room not found: missing"


def test_read_booking_request_returns_404_when_customer_is_not_created(
    monkeypatch,
    booking_request: BookingRequest,
    room: Room,
    database: InMemoryDatabase,
) -> None:
    monkeypatch.setattr("api.routers.bookings.get_room", Mock(return_value=room))
    monkeypatch.setattr("api.routers.bookings.create_customer", Mock(return_value=None))

    with pytest.raises(HTTPException) as error:
        read_booking_request(
            booking_request,
            room.room_id,
            "Alex",
            "Morgan",
            "alex@example.com",
            "en",
            database,
        )

    assert error.value.status_code == 404
    assert "Customer not found and not created" in error.value.detail


def test_read_booking_request_converts_value_error_to_422(
    monkeypatch,
    booking_request: BookingRequest,
    room: Room,
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    monkeypatch.setattr("api.routers.bookings.get_room", Mock(return_value=room))
    monkeypatch.setattr(
        "api.routers.bookings.create_customer",
        Mock(return_value=customer),
    )
    monkeypatch.setattr(
        "api.routers.bookings.confirm_booking",
        Mock(side_effect=ValueError("room unavailable")),
    )

    with pytest.raises(HTTPException) as error:
        read_booking_request(
            booking_request,
            room.room_id,
            customer.first_name,
            customer.last_name,
            customer.email,
            customer.preferred_language,
            database,
        )

    assert error.value.status_code == 422
    assert error.value.detail == "room unavailable"


def test_read_booking_request_confirms_and_maps_booking(
    monkeypatch,
    booking_request: BookingRequest,
    room: Room,
    customer: Customer,
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    monkeypatch.setattr("api.routers.bookings.get_room", Mock(return_value=room))
    create_customer = Mock(return_value=customer)
    confirm = Mock(return_value=booking)
    response_from_booking = Mock(return_value="response")
    monkeypatch.setattr("api.routers.bookings.create_customer", create_customer)
    monkeypatch.setattr("api.routers.bookings.confirm_booking", confirm)
    monkeypatch.setattr(
        "api.routers.bookings._response_from_booking",
        response_from_booking,
    )

    assert read_booking_request(
        booking_request,
        room.room_id,
        customer.first_name,
        customer.last_name,
        customer.email,
        customer.preferred_language,
        database,
    ) == "response"
    confirm.assert_called_once_with(
        booking_request=booking_request,
        room=room,
        customer=customer,
        database=database,
    )


def test_response_from_booking_builds_public_schema(
    booking: Booking,
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    database.customers.append(customer)

    response = _response_from_booking(booking, database)

    assert response is not None
    assert response.booking_id == booking.booking_id
    assert response.guest_name == customer.full_name
    assert response.hotel_name == database.hotel_name
    assert response.hotel_address == database.hotel_address
    assert response.status == booking.status


@pytest.mark.parametrize("missing", ["booking", "customer"])
def test_response_from_booking_returns_404_for_missing_required_object(
    missing: str,
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    selected_booking = None if missing == "booking" else booking

    with pytest.raises(HTTPException) as error:
        _response_from_booking(selected_booking, database)

    assert error.value.status_code == 404
    assert missing in error.value.detail
