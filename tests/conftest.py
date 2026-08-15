from __future__ import annotations

import sys
from contextlib import nullcontext
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib.util import find_spec
from types import ModuleType, SimpleNamespace
from typing import NoReturn

import pytest


class _UnavailablePretrainedDependency:
    """Fail clearly if a unit test accidentally loads a real local model."""

    @classmethod
    def from_pretrained(cls, *args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("Local model loading is disabled in unit tests")


def _unavailable_dependency(*args: object, **kwargs: object) -> NoReturn:
    raise RuntimeError("Optional model dependency is disabled in unit tests")


def _install_optional_model_stubs() -> None:
    """Make production adapters importable without heavyweight model runtimes."""

    if find_spec("torch") is None:
        torch = ModuleType("torch")
        torch.cuda = SimpleNamespace(is_available=lambda: False)
        torch.xpu = SimpleNamespace(is_available=lambda: False)
        torch.device = lambda value: value
        torch.inference_mode = nullcontext
        torch.set_num_threads = lambda value: None
        torch.set_num_interop_threads = lambda value: None
        torch.softmax = _unavailable_dependency
        torch.argmax = _unavailable_dependency
        sys.modules["torch"] = torch

    if find_spec("transformers") is None:
        transformers = ModuleType("transformers")
        transformers.AutoModelForSeq2SeqLM = _UnavailablePretrainedDependency
        transformers.AutoModelForSequenceClassification = (
            _UnavailablePretrainedDependency
        )
        transformers.AutoTokenizer = _UnavailablePretrainedDependency
        transformers.M2M100ForConditionalGeneration = (
            _UnavailablePretrainedDependency
        )
        transformers.M2M100Tokenizer = _UnavailablePretrainedDependency
        sys.modules["transformers"] = transformers

    if find_spec("fasttext") is None:
        fasttext = ModuleType("fasttext")
        fasttext.load_model = _unavailable_dependency
        sys.modules["fasttext"] = fasttext

    if find_spec("llama_cpp") is None:
        llama_cpp = ModuleType("llama_cpp")
        llama_types = ModuleType("llama_cpp.llama_types")
        llama_cpp.Llama = _UnavailablePretrainedDependency
        llama_types.CreateChatCompletionResponse = dict
        sys.modules["llama_cpp"] = llama_cpp
        sys.modules["llama_cpp.llama_types"] = llama_types

    if find_spec("huggingface_hub") is None:
        huggingface_hub = ModuleType("huggingface_hub")
        huggingface_hub.hf_hub_download = _unavailable_dependency
        sys.modules["huggingface_hub"] = huggingface_hub


_install_optional_model_stubs()

from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.customer import Customer
from domain.entities.room import Room
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod


class InMemoryDatabase(DatabaseInterface):
    """Small deterministic database double used by domain and API tests."""

    def __init__(self) -> None:
        self.rooms: list[Room] = []
        self.bookings: list[Booking] = []
        self.customers: list[Customer] = []
        self.information: dict[InformationTopic, str] = {}
        self.breakfast_price = Money(Decimal("12.50"), "EUR")
        self.hotel_name = "Harbour Light Hotel"
        self.hotel_address = "1 Harbour Way, 12345 Seaside, DE"
        self.saved_bookings: list[Booking] = []
        self.saved_customers: list[Customer] = []

    def get_rooms(self) -> list[Room]:
        return list(self.rooms)

    def get_room(self, room_id: str) -> Room | None:
        return next((room for room in self.rooms if room.room_id == room_id), None)

    def get_bookings(self) -> list[Booking]:
        return list(self.bookings)

    def get_booking(self, booking_id: str) -> Booking | None:
        return next(
            (booking for booking in self.bookings if booking.booking_id == booking_id),
            None,
        )

    def save_booking(self, booking: Booking) -> None:
        self.saved_bookings.append(booking)
        for index, current in enumerate(self.bookings):
            if current.booking_id == booking.booking_id:
                self.bookings[index] = booking
                break
        else:
            self.bookings.append(booking)

    def get_customers(self) -> list[Customer]:
        return list(self.customers)

    def get_customer(self, customer_id: str) -> Customer | None:
        return next(
            (
                customer
                for customer in self.customers
                if customer.customer_id == customer_id
            ),
            None,
        )

    def identify_customer(
        self,
        first_name: str,
        last_name: str,
        email: str,
    ) -> Customer | None:
        return next(
            (
                customer
                for customer in self.customers
                if (
                    customer.first_name,
                    customer.last_name,
                    customer.email,
                )
                == (first_name, last_name, email)
            ),
            None,
        )

    def save_customer(self, customer: Customer) -> None:
        self.saved_customers.append(customer)
        for index, current in enumerate(self.customers):
            if current.customer_id == customer.customer_id:
                self.customers[index] = customer
                break
        else:
            self.customers.append(customer)

    def get_breakfast_price(self) -> Money:
        return self.breakfast_price

    def get_information(self, topic: InformationTopic) -> str | None:
        return self.information.get(topic)

    def get_hotel_name(self) -> str:
        return self.hotel_name

    def get_hotel_address(self) -> str:
        return self.hotel_address

    def get_booking_by_name(
        self,
        last_name: str,
        email: str,
        check_in: date,
    ) -> Booking | None:
        customer_ids = {
            customer.customer_id
            for customer in self.customers
            if customer.last_name == last_name and customer.email == email
        }
        return next(
            (
                booking
                for booking in self.bookings
                if booking.customer_id in customer_ids
                and booking.stay_period.check_in == check_in
                and booking.status is not BookingStatus.CANCELLED
            ),
            None,
        )

    def mail_is_in_use(self, email: str) -> bool:
        return any(customer.email == email for customer in self.customers)


@pytest.fixture
def stay_period() -> StayPeriod:
    return StayPeriod(check_in=date(2030, 6, 10), check_out=date(2030, 6, 13))


@pytest.fixture
def room() -> Room:
    return Room(
        room_id="room-101",
        room_number="101",
        floor=1,
        category=RoomCategory.DOUBLE,
        max_occupancy=2,
        price_per_night=Money(Decimal("100.00"), "EUR"),
        is_accessible=True,
    )


@pytest.fixture
def booking_request(stay_period: StayPeriod) -> BookingRequest:
    return BookingRequest(
        request_id="request-1",
        stay_period=stay_period,
        guest_count=2,
        breakfast_included=False,
        accessible_requested=False,
    )


@pytest.fixture
def customer() -> Customer:
    return Customer(
        customer_id="customer-1",
        first_name="Alex",
        last_name="Morgan",
        email="alex@example.com",
    )


@pytest.fixture
def booking(stay_period: StayPeriod) -> Booking:
    return Booking(
        booking_id="booking-1",
        customer_id="customer-1",
        room_id="room-101",
        stay_period=stay_period,
        guest_count=2,
        total_price=Money(Decimal("300.00"), "EUR"),
        status=BookingStatus.CONFIRMED,
        created_at=datetime(2030, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def database() -> InMemoryDatabase:
    return InMemoryDatabase()
