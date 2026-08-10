from datetime import date

import pytest
from conftest import InMemoryDatabase

from conversation.entities.information import Information
from conversation.graph.nodes import DatabaseDomainAdapter
from conversation.graph.state import DomainOperation
from conversation.value_object.information_fields import InformationField
from domain.entities.booking import Booking
from domain.entities.customer import Customer
from domain.entities.room import Room
from domain.services.find_matching_rooms import MatchResponse
from domain.value_objects.room_category import RoomCategory


def availability_information() -> dict[InformationField, Information]:
    return {
        InformationField.CHECK_IN: Information(
            InformationField.CHECK_IN,
            date(2030, 6, 10),
        ),
        InformationField.CHECK_OUT: Information(
            InformationField.CHECK_OUT,
            date(2030, 6, 13),
        ),
        InformationField.GUEST_COUNT: Information(
            InformationField.GUEST_COUNT,
            2,
        ),
        InformationField.ACCESSIBLE: Information(
            InformationField.ACCESSIBLE,
            False,
        ),
    }


def booking_identity_information(
    booking: Booking,
    customer: Customer,
) -> dict[InformationField, Information]:
    return {
        InformationField.LAST_NAME: Information(
            InformationField.LAST_NAME,
            customer.last_name,
        ),
        InformationField.EMAIL: Information(
            InformationField.EMAIL,
            customer.email,
        ),
        InformationField.CHECK_IN: Information(
            InformationField.CHECK_IN,
            booking.stay_period.check_in,
        ),
    }


def test_database_adapter_finds_availability(
    room: Room,
    database: InMemoryDatabase,
) -> None:
    database.rooms.append(room)
    adapter = DatabaseDomainAdapter(database)

    result = adapter.execute(
        DomainOperation.FIND_AVAILABILITY,
        availability_information(),
    )

    assert isinstance(result, MatchResponse)
    assert result.rooms == [room]


def test_database_adapter_uses_optional_breakfast_value(
    room: Room,
    database: InMemoryDatabase,
) -> None:
    database.rooms.append(room)
    information = availability_information()
    information[InformationField.BREAKFAST] = Information(
        InformationField.BREAKFAST,
        True,
    )

    result = DatabaseDomainAdapter(database).execute(
        DomainOperation.FIND_AVAILABILITY,
        information,
    )

    assert isinstance(result, MatchResponse)
    assert result.rooms == [room]
    assert result.request.breakfast_included is True


def test_database_adapter_gets_booking(
    booking: Booking,
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    database.customers.append(customer)
    database.bookings.append(booking)
    information = booking_identity_information(booking, customer)

    assert (
        DatabaseDomainAdapter(database).execute(
            DomainOperation.GET_BOOKING,
            information,
        )
        is booking
    )


def test_database_adapter_cancels_booking(
    booking: Booking,
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    database.customers.append(customer)
    database.bookings.append(booking)
    information = booking_identity_information(booking, customer)

    assert (
        DatabaseDomainAdapter(database).execute(
            DomainOperation.CANCEL_BOOKING,
            information,
        )
        is booking
    )
    assert database.saved_bookings == [booking]


def test_database_adapter_requires_room_category_for_booking_creation(
    database: InMemoryDatabase,
) -> None:
    with pytest.raises(KeyError, match="room_category"):
        DatabaseDomainAdapter(database).execute(
            DomainOperation.CREATE_BOOKING,
            {},
        )


def test_database_adapter_creates_customer_and_booking(
    room: Room,
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    database.rooms.append(room)
    information = availability_information()
    information.update(
        {
            InformationField.ROOM_CATEGORY: Information(
                InformationField.ROOM_CATEGORY,
                RoomCategory.DOUBLE,
            ),
            InformationField.FIRST_NAME: Information(
                InformationField.FIRST_NAME,
                customer.first_name,
            ),
            InformationField.LAST_NAME: Information(
                InformationField.LAST_NAME,
                customer.last_name,
            ),
            InformationField.EMAIL: Information(
                InformationField.EMAIL,
                customer.email,
            ),
            InformationField.PREFERRED_LANG: Information(
                InformationField.PREFERRED_LANG,
                customer.preferred_language,
            ),
        }
    )

    result = DatabaseDomainAdapter(database).execute(
        DomainOperation.CREATE_BOOKING,
        information,
    )

    assert isinstance(result, Booking)
    assert result.room_id == room.room_id
    assert len(database.saved_customers) == 1
    assert database.saved_bookings == [result]


def test_database_adapter_reports_missing_required_information(
    database: InMemoryDatabase,
) -> None:
    with pytest.raises(KeyError, match="last_name"):
        DatabaseDomainAdapter(database).execute(DomainOperation.GET_BOOKING, {})
