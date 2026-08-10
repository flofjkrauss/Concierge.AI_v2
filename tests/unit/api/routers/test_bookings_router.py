from unittest.mock import Mock

import pytest
from conftest import InMemoryDatabase
from fastapi import HTTPException

from api.routers.bookings import (
    _response_from_booking,
    read_booking,
    read_booking_by_name,
    read_booking_request,
    read_booking_to_cancel,
    read_booking_to_cancel_by_name,
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

    assert read_booking(database=database, booking_id="booking-1") == "response"
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

    assert (
        read_booking_to_cancel(
            database=database,
            booking_id="booking-1",
        )
        == "response"
    )
    cancel.assert_called_once_with(booking_id="booking-1", database=database)


def test_read_booking_request_returns_404_for_unknown_room_category(
    booking_request: BookingRequest,
    database: InMemoryDatabase,
) -> None:
    with pytest.raises(HTTPException) as error:
        read_booking_request(
            database=database,
            booking_request=booking_request,
            room_category="missing",
            first_name="Alex",
            last_name="Morgan",
            email="alex@example.com",
            preferred_language="en",
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Room category not found: missing"


def test_read_booking_request_returns_404_when_customer_is_not_created(
    monkeypatch,
    booking_request: BookingRequest,
    room: Room,
    database: InMemoryDatabase,
) -> None:
    monkeypatch.setattr("api.routers.bookings.create_customer", Mock(return_value=None))

    with pytest.raises(HTTPException) as error:
        read_booking_request(
            database=database,
            booking_request=booking_request,
            room_category=room.category,
            first_name="Alex",
            last_name="Morgan",
            email="alex@example.com",
            preferred_language="en",
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
            database=database,
            booking_request=booking_request,
            room_category=room.category,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=customer.email,
            preferred_language=customer.preferred_language,
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
    create_customer = Mock(return_value=customer)
    confirm = Mock(return_value=booking)
    response_from_booking = Mock(return_value="response")
    monkeypatch.setattr("api.routers.bookings.create_customer", create_customer)
    monkeypatch.setattr("api.routers.bookings.confirm_booking", confirm)
    monkeypatch.setattr(
        "api.routers.bookings._response_from_booking",
        response_from_booking,
    )

    assert (
        read_booking_request(
            database=database,
            booking_request=booking_request,
            room_category=room.category,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=customer.email,
            preferred_language=customer.preferred_language,
        )
        == "response"
    )
    confirm.assert_called_once_with(
        booking_request=booking_request,
        room_category=room.category,
        customer=customer,
        database=database,
    )


def test_response_from_booking_builds_public_schema(
    booking: Booking,
    customer: Customer,
    room: Room,
    database: InMemoryDatabase,
) -> None:
    database.customers.append(customer)
    database.rooms.append(room)

    response = _response_from_booking(booking, database)

    assert response is not None
    assert response.booking_id == booking.booking_id
    assert response.guest_name == customer.full_name
    assert response.hotel_name == database.hotel_name
    assert response.hotel_address == database.hotel_address
    assert response.status == booking.status


def test_read_booking_by_name_normalizes_date_and_maps_result(
    monkeypatch,
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    get_booking = Mock(return_value=booking)
    response_from_booking = Mock(return_value="response")
    monkeypatch.setattr("api.routers.bookings.get_booking_by_name", get_booking)
    monkeypatch.setattr(
        "api.routers.bookings._response_from_booking",
        response_from_booking,
    )

    result = read_booking_by_name(
        database=database,
        last_name="Morgan",
        email="alex@example.com",
        check_in="2030-06-10",
    )

    assert result == "response"
    get_booking.assert_called_once_with(
        last_name="Morgan",
        email="alex@example.com",
        check_in=booking.stay_period.check_in,
        database=database,
    )


def test_read_booking_by_name_returns_none_for_invalid_date(
    monkeypatch,
    database: InMemoryDatabase,
) -> None:
    get_booking = Mock()
    monkeypatch.setattr("api.routers.bookings.get_booking_by_name", get_booking)

    assert (
        read_booking_by_name(
            database=database,
            last_name="Morgan",
            email="alex@example.com",
            check_in="not-a-date",
        )
        is None
    )
    get_booking.assert_not_called()


def test_read_booking_to_cancel_by_name_delegates(
    monkeypatch,
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    cancel = Mock(return_value=booking)
    response_from_booking = Mock(return_value="response")
    monkeypatch.setattr("api.routers.bookings.cancel_booking_by_name", cancel)
    monkeypatch.setattr(
        "api.routers.bookings._response_from_booking",
        response_from_booking,
    )

    result = read_booking_to_cancel_by_name(
        database=database,
        last_name="Morgan",
        email="alex@example.com",
        check_in="2030-06-10",
    )

    assert result == "response"
    cancel.assert_called_once_with(
        last_name="Morgan",
        email="alex@example.com",
        check_in=booking.stay_period.check_in,
        database=database,
    )


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
