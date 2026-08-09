from datetime import date

import pytest
from conftest import InMemoryDatabase

from conversation.entities.information import Information
from conversation.graph.nodes import DatabaseDomainAdapter
from conversation.graph.state import DomainOperation
from conversation.value_object.information_fields import InformationField
from domain.entities.booking import Booking
from domain.entities.room import Room


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

    assert result == [room]


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

    assert DatabaseDomainAdapter(database).execute(
        DomainOperation.FIND_AVAILABILITY,
        information,
    ) == [room]


def test_database_adapter_gets_booking(
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    database.bookings.append(booking)
    information = {
        InformationField.BOOKING_ID: Information(
            InformationField.BOOKING_ID,
            booking.booking_id,
        )
    }

    assert DatabaseDomainAdapter(database).execute(
        DomainOperation.GET_BOOKING,
        information,
    ) is booking


def test_database_adapter_cancels_booking(
    booking: Booking,
    database: InMemoryDatabase,
) -> None:
    database.bookings.append(booking)
    information = {
        InformationField.BOOKING_ID: Information(
            InformationField.BOOKING_ID,
            booking.booking_id,
        )
    }

    assert DatabaseDomainAdapter(database).execute(
        DomainOperation.CANCEL_BOOKING,
        information,
    ) is booking
    assert database.saved_bookings == [booking]


def test_database_adapter_requires_explicit_booking_creator(
    database: InMemoryDatabase,
) -> None:
    with pytest.raises(RuntimeError, match="No room must be selected implicitly"):
        DatabaseDomainAdapter(database).execute(
            DomainOperation.CREATE_BOOKING,
            {},
        )


def test_database_adapter_delegates_to_booking_creator(
    database: InMemoryDatabase,
) -> None:
    calls: list[tuple[object, object]] = []

    def creator(information, received_database):
        calls.append((information, received_database))
        return "created"

    information = availability_information()
    adapter = DatabaseDomainAdapter(database, booking_creator=creator)

    assert adapter.execute(DomainOperation.CREATE_BOOKING, information) == "created"
    assert calls == [(information, database)]


def test_database_adapter_reports_missing_required_information(
    database: InMemoryDatabase,
) -> None:
    with pytest.raises(KeyError, match="booking_id"):
        DatabaseDomainAdapter(database).execute(DomainOperation.GET_BOOKING, {})
