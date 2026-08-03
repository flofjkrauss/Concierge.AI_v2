"""Booking domain entity."""

from dataclasses import dataclass

from domain.value_objects.stay_period import StayPeriod


@dataclass(slots=True)
class BookingRequest:
    """booking request domain entity."""

    request_id: str
    stay_period: StayPeriod
    guest_count: int
    breakfast_included: bool = False
    accessible_requested: bool = False

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty")

        if self.guest_count < 1:
            raise ValueError("guest_count must be at least 1")

    def __str__(self) -> str:
        retval = f"Booking request {self.request_id}: {self.guest_count} guests {self.stay_period}."
        retval += f"Breakfast included: {self.breakfast_included}"
        retval += f"Accessability requested: {self.accessible_requested}"
        return retval