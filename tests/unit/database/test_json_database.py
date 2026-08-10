from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from database.json_database import JsonDatabase
from domain.entities.booking import Booking
from domain.entities.customer import Customer
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def make_data_directory(tmp_path: Path) -> Path:
    write_json(
        tmp_path / "hotel_assets.json",
        {
            "hotel": {
                "name": "Harbour Light Hotel",
                "currency": "EUR",
                "breakfast_price": "15.00",
                "address": {
                    "street": "1 Harbour Way",
                    "postal_code": "12345",
                    "city": "Seaside",
                    "country_code": "DE",
                },
            },
            "rooms": [
                {
                    "room_id": "room-101",
                    "number": "101",
                    "floor": 1,
                    "category_id": "double",
                    "max_occupancy": 2,
                    "price_per_night": "120.00",
                    "accessible": True,
                    "in_service": True,
                }
            ],
        },
    )
    write_json(
        tmp_path / "customers.json",
        {
            "customers": [
                {
                    "customer_id": "customer-1",
                    "first_name": "Alex",
                    "last_name": "Morgan",
                    "email": "alex@example.com",
                    "phone": None,
                    "preferred_language": "en",
                    "created_at": "2029-01-01T00:00:00+00:00",
                }
            ]
        },
    )
    write_json(
        tmp_path / "bookings.json",
        {
            "bookings": [
                {
                    "booking_id": "booking-1",
                    "customer_id": "customer-1",
                    "room_id": "room-101",
                    "guest_name": "Alex Morgan",
                    "arrival": "2030-06-10",
                    "departure": "2030-06-13",
                    "guests": 2,
                    "breakfast": True,
                    "accessible_requested": False,
                    "total_price": "405.00",
                    "currency": "EUR",
                    "status": "confirmed",
                    "booked_at": "2030-01-01T00:00:00+00:00",
                    "cancelled_at": None,
                }
            ]
        },
    )
    write_json(
        tmp_path / "hotel_information.json",
        {"information": [{"topic": "wifi", "answer": "Wi-Fi is complimentary."}]},
    )
    return tmp_path


@pytest.fixture
def data_directory(tmp_path: Path) -> Path:
    return make_data_directory(tmp_path)


@pytest.fixture
def json_database(data_directory: Path) -> JsonDatabase:
    return JsonDatabase(data_directory)


def test_init_reports_all_missing_required_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as error:
        JsonDatabase(tmp_path)

    assert "bookings.json" in str(error.value)
    assert "customers.json" in str(error.value)
    assert "hotel_assets.json" in str(error.value)
    assert "hotel_information.json" in str(error.value)


def test_get_rooms_converts_json_records(json_database: JsonDatabase) -> None:
    rooms = json_database.get_rooms()

    assert len(rooms) == 1
    assert rooms[0].room_id == "room-101"
    assert rooms[0].category is RoomCategory.DOUBLE
    assert rooms[0].price_per_night == Money(Decimal("120.00"), "EUR")
    assert rooms[0].is_accessible


def test_get_room_returns_match_or_none(json_database: JsonDatabase) -> None:
    assert json_database.get_room("room-101") is not None
    assert json_database.get_room("missing") is None


def test_room_record_requires_capacity_and_price(data_directory: Path) -> None:
    data = json.loads((data_directory / "hotel_assets.json").read_text())
    del data["rooms"][0]["max_occupancy"]
    write_json(data_directory / "hotel_assets.json", data)

    with pytest.raises(ValueError, match="max_occupancy"):
        JsonDatabase(data_directory).get_rooms()


def test_get_bookings_converts_json_records(json_database: JsonDatabase) -> None:
    booking = json_database.get_bookings()[0]

    assert booking.booking_id == "booking-1"
    assert booking.status is BookingStatus.CONFIRMED
    assert booking.stay_period == StayPeriod(date(2030, 6, 10), date(2030, 6, 13))
    assert booking.created_at == datetime(2030, 1, 1, tzinfo=UTC)


def test_get_booking_normalizes_id_and_handles_missing(
    json_database: JsonDatabase,
) -> None:
    assert json_database.get_booking(" booking-1 ") is not None
    assert json_database.get_booking("missing") is None


def test_get_booking_rejects_blank_id(json_database: JsonDatabase) -> None:
    with pytest.raises(ValueError, match="booking_id must not be empty"):
        json_database.get_booking(" ")


def test_get_booking_by_name_returns_active_matching_booking(
    json_database: JsonDatabase,
) -> None:
    booking = json_database.get_booking_by_name(
        last_name="Morgan",
        email="alex@example.com",
        check_in=date(2030, 6, 10),
    )

    assert booking is not None
    assert booking.booking_id == "booking-1"


def test_get_booking_by_name_returns_none_for_unknown_customer(
    json_database: JsonDatabase,
) -> None:
    assert (
        json_database.get_booking_by_name(
            last_name="Unknown",
            email="unknown@example.com",
            check_in=date(2030, 6, 10),
        )
        is None
    )


def test_mail_is_in_use_checks_persisted_customers(
    json_database: JsonDatabase,
) -> None:
    assert json_database.mail_is_in_use("alex@example.com")
    assert not json_database.mail_is_in_use("unknown@example.com")


def test_save_booking_inserts_json_record(
    json_database: JsonDatabase,
    data_directory: Path,
) -> None:
    booking = Booking(
        booking_id="booking-2",
        customer_id="customer-1",
        room_id="room-101",
        stay_period=StayPeriod(date(2030, 7, 1), date(2030, 7, 3)),
        guest_count=1,
        total_price=Money(Decimal("240.00"), "EUR"),
        status=BookingStatus.CONFIRMED,
        created_at=datetime(2030, 2, 1, tzinfo=UTC),
    )

    json_database.save_booking(booking)

    records = json.loads((data_directory / "bookings.json").read_text())["bookings"]
    saved = next(record for record in records if record["booking_id"] == "booking-2")
    assert saved["guest_name"] == "Alex Morgan"
    assert saved["total_price"] == "240.00"
    assert not (data_directory / "bookings.json.tmp").exists()


def test_save_booking_updates_existing_record(
    json_database: JsonDatabase,
    data_directory: Path,
) -> None:
    booking = json_database.get_booking("booking-1")
    assert booking is not None
    booking.status = BookingStatus.CANCELLED

    json_database.save_booking(booking)
    first_cancelled_at = json.loads((data_directory / "bookings.json").read_text())[
        "bookings"
    ][0]["cancelled_at"]
    json_database.save_booking(booking)
    second_cancelled_at = json.loads((data_directory / "bookings.json").read_text())[
        "bookings"
    ][0]["cancelled_at"]

    assert first_cancelled_at is not None
    assert second_cancelled_at == first_cancelled_at


def test_save_booking_requires_existing_customer(json_database: JsonDatabase) -> None:
    booking = json_database.get_booking("booking-1")
    assert booking is not None
    booking.customer_id = "missing"

    with pytest.raises(ValueError, match="customer missing does not exist"):
        json_database.save_booking(booking)


def test_customer_reads_lookup_and_identification(json_database: JsonDatabase) -> None:
    customer = json_database.get_customer(" customer-1 ")

    assert customer is not None
    assert customer.full_name == "Alex Morgan"
    assert json_database.get_customer("missing") is None
    assert (
        json_database.identify_customer(
            "Alex",
            "Morgan",
            "alex@example.com",
        )
        == customer
    )
    assert json_database.identify_customer("Alex", "Other", "alex@example.com") is None


def test_get_customers_returns_all_customer_records(
    json_database: JsonDatabase,
) -> None:
    customers = json_database.get_customers()

    assert len(customers) == 1
    assert customers[0].customer_id == "customer-1"


def test_get_customer_rejects_blank_id(json_database: JsonDatabase) -> None:
    with pytest.raises(ValueError, match="customer_id must not be empty"):
        json_database.get_customer(" ")


def test_save_customer_inserts_and_then_updates_record(
    json_database: JsonDatabase,
    data_directory: Path,
) -> None:
    customer = Customer("customer-2", "Sam", "Lee", "sam@example.com")

    json_database.save_customer(customer)
    first_record = json.loads((data_directory / "customers.json").read_text())[
        "customers"
    ][1]
    customer.phone = "+49 123"
    json_database.save_customer(customer)
    second_record = json.loads((data_directory / "customers.json").read_text())[
        "customers"
    ][1]

    assert second_record["phone"] == "+49 123"
    assert second_record["created_at"] == first_record["created_at"]


def test_hotel_values_are_read_from_json(json_database: JsonDatabase) -> None:
    assert json_database.get_breakfast_price() == Money(Decimal("15.00"), "EUR")
    assert json_database.get_information(InformationTopic.WIFI) == (
        "Wi-Fi is complimentary."
    )
    assert json_database.get_information(InformationTopic.PETS) is None
    assert json_database.get_hotel_name() == "Harbour Light Hotel"
    assert json_database.get_hotel_address() == ("1 Harbour Way, 12345 Seaside, DE")


def test_get_information_rejects_empty_topic(json_database: JsonDatabase) -> None:
    with pytest.raises(ValueError, match="topic must not be empty"):
        json_database.get_information(None)  # type: ignore[arg-type]


def test_json_reader_rejects_non_object_document(data_directory: Path) -> None:
    write_json(data_directory / "hotel_assets.json", [])

    with pytest.raises(TypeError, match="Expected a JSON object"):
        JsonDatabase(data_directory).get_rooms()
