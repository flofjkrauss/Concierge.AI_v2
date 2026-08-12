"""JSON-based implementation of the database interface."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from threading import RLock
from typing import Any

from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.entities.customer import Customer
from domain.entities.room import Room
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod


class JsonDatabase(DatabaseInterface):
    """Store and retrieve application data using JSON files."""

    def __init__(self, data_directory: Path) -> None:
        self._data_directory = data_directory
        self._bookings_path = data_directory / "bookings.json"
        self._customers_path = data_directory / "customers.json"
        self._hotel_assets_path = data_directory / "hotel_assets.json"
        self._hotel_information_path = (
            data_directory / "hotel_information.json"
        )
        self._lock = RLock()

        self._validate_files_exist()

    def get_room(self, room_id: str) -> Room | None:
        """Return one specific room."""        
        with self._lock:
            data = self._read_json(self._hotel_assets_path)

        hotel_currency = data["hotel"]["currency"]
        for record in data["rooms"]:
            if record["room_id"] == room_id:
                room = self._room_from_record(record=record, currency=hotel_currency)
                return room
            
        return None

    def get_rooms(self) -> list[Room]:
        """Return all rooms from the hotel-assets file."""

        with self._lock:
            data = self._read_json(self._hotel_assets_path)

        hotel_currency = data["hotel"]["currency"]

        return [
            self._room_from_record(
                record=record,
                currency=hotel_currency,
            )
            for record in data["rooms"]
        ]

    def get_bookings(self) -> list[Booking]:
        """Return all bookings from the bookings file."""

        with self._lock:
            data = self._read_json(self._bookings_path)

        return [
            self._booking_from_record(record)
            for record in data["bookings"]
        ]

    def get_booking(self, booking_id: str) -> Booking | None:
        """Return the booking with the given ID."""

        normalized_id = booking_id.strip()

        if not normalized_id:
            raise ValueError("booking_id must not be empty")

        with self._lock:
            data = self._read_json(self._bookings_path)

        for record in data["bookings"]:
            if record["booking_id"] == normalized_id:
                return self._booking_from_record(record)

        return None

    def save_booking(self, booking: Booking) -> None:
        """Insert a new booking or update an existing booking."""

        with self._lock:
            data = self._read_json(self._bookings_path)
            records = data["bookings"]

            existing_index = next(
                (
                    index
                    for index, record in enumerate(records)
                    if record["booking_id"] == booking.booking_id
                ),
                None,
            )

            existing_record = (
                records[existing_index]
                if existing_index is not None
                else None
            )

            record = self._booking_to_record(
                booking=booking,
                existing_record=existing_record,
            )

            if existing_index is None:
                records.append(record)
            else:
                records[existing_index] = record

            self._write_json(
                path=self._bookings_path,
                data=data,
            )

    def get_customers(self) -> list[Customer]:
        """Return all customers from the customers file."""

        with self._lock:
            data = self._read_json(self._customers_path)

        return [
            self._customer_from_record(record)
            for record in data["customers"]
        ]

    def get_customer(self, customer_id: str) -> Customer | None:
        """Return the customer with the given ID."""

        normalized_id = customer_id.strip()

        if not normalized_id:
            raise ValueError("customer_id must not be empty")

        with self._lock:
            data = self._read_json(self._customers_path)

        for record in data["customers"]:
            if record["customer_id"] == normalized_id:
                return self._customer_from_record(record)

        return None

    def identify_customer(
            self, first_name: str ,
            last_name: str,
            email: str) -> Customer | None:
         with self._lock:
            data = self._read_json(self._customers_path)

            for record in data["customers"]:
                if all([
                    (record["first_name"] == first_name),
                    (record["last_name"] == last_name),
                    (record["email"] == email)
                ]):
                    return self.get_customer(record["customer_id"])
                    
            return None

    def save_customer(self, customer: Customer) -> None:
        """Insert a new customer or update an existing customer."""

        with self._lock:
            data = self._read_json(self._customers_path)
            records = data["customers"]

            existing_index = next(
                (
                    index
                    for index, record in enumerate(records)
                    if record["customer_id"] == customer.customer_id
                ),
                None,
            )

            existing_record = (
                records[existing_index]
                if existing_index is not None
                else None
            )

            record = self._customer_to_record(
                customer=customer,
                existing_record=existing_record,
            )

            if existing_index is None:
                records.append(record)
            else:
                records[existing_index] = record

            self._write_json(
                path=self._customers_path,
                data=data,
            )

    def get_breakfast_price(self) -> Money:
        """Return the breakfast price per person and night."""

        with self._lock:
            data = self._read_json(self._hotel_assets_path)

        hotel = data["hotel"]

        raw_price = hotel.get("breakfast_price")

        return Money(
            amount=Decimal(raw_price),
            currency=hotel["currency"],
        )

    def get_information(self, topic: InformationTopic) -> str | None:
        """Return the answer stored for a hotel-information topic."""

        if not topic:
            raise ValueError("topic must not be empty")

        with self._lock:
            data = self._read_json(self._hotel_information_path)

        for record in data["information"]:
            if record["topic"].lower() == topic:
                return str(record["answer"])

        return None

    def get_hotel_name(self) -> str:
        with self._lock:
            data = self._read_json(self._hotel_assets_path)
            return str(data["hotel"]["name"])

    def get_hotel_address(self) -> str:
        with self._lock:
            data = self._read_json(self._hotel_assets_path)
            address_data = data["hotel"]["address"]
            return f"{address_data["street"]}, {address_data["postal_code"]} {address_data["city"]}, {address_data["country_code"]}"

    def _room_from_record(
        self,
        record: dict[str, Any],
        currency: str,
    ) -> Room:
        """Convert a JSON room record into a Room entity."""

        missing_fields = {
            field
            for field in ("max_occupancy", "price_per_night")
            if field not in record
        }

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(
                f"Room {record.get('room_id', '<unknown>')} "
                f"is missing required fields: {missing}"
            )

        return Room(
            room_id=record["room_id"],
            room_number=record["number"],
            floor=record["floor"],
            category=RoomCategory(record["category_id"]),
            max_occupancy=int(record["max_occupancy"]),
            price_per_night=Money(
                amount=Decimal(record["price_per_night"]),
                currency=currency,
            ),
            is_accessible=bool(record["accessible"]),
            is_bookable=bool(record["in_service"]),
        )

    def get_booking_by_name(self, last_name: str, email: str, check_in: date) -> Booking | None:
        """Return the booking with the given last_name email combination."""

        with self._lock:
            customer_data = self._read_json(self._customers_path)
            data = self._read_json(self._bookings_path)

            customer: Customer | None = None
            for record in customer_data["customers"]:
                if record["email"] == email and record["last_name"] == last_name:
                    customer = self._customer_from_record(record=record)
                    break
            
            if not customer:
                return None

            for record in data["bookings"]:
                if record["customer_id"] == customer.customer_id:
                    record_check_in = date.fromisoformat(record["arrival"])
                    if record_check_in == check_in:
                        booking = self._booking_from_record(record)
                        if booking.status != BookingStatus.CANCELLED:
                            return booking
    
            return None

    def mail_is_in_use(self, email: str) -> bool:
        """check if mail address is already in use"""
        with self._lock:
            data = self._read_json(self._customers_path)
            for record in data["customers"]:
                if record["email"] == email:
                    return True
            
            return False
        

    @staticmethod
    def _booking_from_record(
        record: dict[str, Any],
    ) -> Booking:
        """Convert a JSON booking record into a Booking entity."""

        return Booking(
            booking_id=record["booking_id"],
            customer_id=record["customer_id"],
            room_id=record["room_id"],
            stay_period=StayPeriod(
                check_in=date.fromisoformat(record["arrival"]),
                check_out=date.fromisoformat(record["departure"]),
            ),
            guest_count=int(record["guests"]),
            total_price=Money(
                amount=Decimal(record["total_price"]),
                currency=record["currency"],
            ),
            status=BookingStatus(record["status"]),
            breakfast_included=bool(record["breakfast"]),
            accessible_requested=bool(
                record.get("accessible_requested", False)
            ),
            created_at=datetime.fromisoformat(record["booked_at"]),
        )

    def _booking_to_record(
        self,
        booking: Booking,
        existing_record: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Convert a Booking entity into a JSON record."""

        customer = self.get_customer(booking.customer_id)

        if customer is None:
            raise ValueError(
                f"Cannot save booking {booking.booking_id}: "
                f"customer {booking.customer_id} does not exist"
            )

        cancelled_at: str | None = None

        if booking.status == BookingStatus.CANCELLED:
            existing_cancelled_at = (
                existing_record.get("cancelled_at")
                if existing_record is not None
                else None
            )
            cancelled_at = (
                existing_cancelled_at
                or datetime.now(UTC).isoformat()
            )

        return {
            "booking_id": booking.booking_id,
            "customer_id": booking.customer_id,
            "room_id": booking.room_id,
            "guest_name": (
                f"{customer.first_name} {customer.last_name}"
            ),
            "arrival": booking.stay_period.check_in.isoformat(),
            "departure": booking.stay_period.check_out.isoformat(),
            "guests": booking.guest_count,
            "breakfast": booking.breakfast_included,
            "accessible_requested": booking.accessible_requested,
            "total_price": str(booking.total_price.amount),
            "currency": booking.total_price.currency,
            "status": booking.status.value,
            "booked_at": booking.created_at.isoformat(),
            "cancelled_at": cancelled_at,
        }

    @staticmethod
    def _customer_from_record(
        record: dict[str, Any],
    ) -> Customer:
        """Convert a JSON customer record into a Customer entity."""

        return Customer(
            customer_id=record["customer_id"],
            first_name=record["first_name"],
            last_name=record["last_name"],
            email=record["email"],
            phone=record.get("phone"),
            preferred_language=record.get(
                "preferred_language",
                "en",
            ),
        )

    @staticmethod
    def _customer_to_record(
        customer: Customer,
        existing_record: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Convert a Customer entity into a JSON record."""

        created_at = (
            existing_record["created_at"]
            if existing_record is not None
            else datetime.now(UTC).isoformat()
        )

        return {
            "customer_id": customer.customer_id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "email": customer.email,
            "phone": customer.phone,
            "preferred_language": customer.preferred_language,
            "created_at": created_at,
        }

    def _validate_files_exist(self) -> None:
        """Ensure that all required JSON files exist."""

        required_files = (
            self._bookings_path,
            self._customers_path,
            self._hotel_assets_path,
            self._hotel_information_path,
        )

        missing_files = [
            path.name
            for path in required_files
            if not path.is_file()
        ]

        if missing_files:
            missing = ", ".join(missing_files)
            raise FileNotFoundError(
                f"Missing database files: {missing}"
            )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        """Read and decode a JSON object."""

        with path.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise TypeError(
                f"Expected a JSON object in {path}"
            )

        return data

    @staticmethod
    def _write_json(
        path: Path,
        data: dict[str, Any],
    ) -> None:
        """Write a JSON object using an atomic file replacement."""

        temporary_path = path.with_suffix(
            f"{path.suffix}.tmp"
        )

        with temporary_path.open(
            mode="w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )
            file.write("\n")

        temporary_path.replace(path)
