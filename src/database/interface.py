"""Generic interface for application data access."""

from abc import ABC, abstractmethod

from domain.entities.booking import Booking
from domain.entities.customer import Customer
from domain.entities.room import Room
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.money import Money


class DatabaseInterface(ABC):
    """Define the data operations required by the business services."""

    @abstractmethod
    def get_rooms(self) -> list[Room]:
        """Return all hotel rooms."""

    @abstractmethod
    def get_bookings(self) -> list[Booking]:
        """Return all bookings."""

    @abstractmethod
    def get_booking(self, booking_id: str) -> Booking | None:
        """Return a booking by its ID."""

    @abstractmethod
    def save_booking(self, booking: Booking) -> None:
        """Insert or update a booking."""

    @abstractmethod
    def get_customers(self) -> list[Customer]:
        """Return all known customers."""

    @abstractmethod
    def get_customer(self, customer_id: str) -> Customer | None:
        """Return a customer by its ID."""

    @abstractmethod
    def save_customer(self, customer: Customer) -> None:
        """Insert or update a customer."""

    @abstractmethod
    def get_breakfast_price(self) -> Money:
        """Return the breakfast price per person and night."""

    @abstractmethod
    def get_information(self, topic: InformationTopic) -> str | None:
        """Return hotel information for a topic."""