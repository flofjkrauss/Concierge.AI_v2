"""Generic interface for application data access."""

from abc import ABC, abstractmethod
from datetime import date

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
    def get_room(self, room_id: str) -> Room | None:
        """Return room by room_id"""

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
    def identify_customer(self, first_name: str, last_name: str, email: str) -> Customer | None:
        """Try to find and already existing customer without knowing his customer_id"""

    @abstractmethod
    def save_customer(self, customer: Customer) -> None:
        """Insert or update a customer."""

    @abstractmethod
    def get_breakfast_price(self) -> Money:
        """Return the breakfast price per person and night."""

    @abstractmethod
    def get_information(self, topic: InformationTopic) -> str | None:
        """Return hotel information for a topic."""

    @abstractmethod
    def get_hotel_name(self) -> str:
        """Return hotel name"""

    @abstractmethod
    def get_hotel_address(self) -> str:
        """Return hotel address"""

    @abstractmethod
    def get_booking_by_name(self, last_name: str, email: str, check_in: date) -> Booking | None:
        """Return a booking by last_name and email combination"""

    @abstractmethod
    def mail_is_in_use(self, email: str) -> bool:
        """ Return if a mail address is already registered by any customer"""