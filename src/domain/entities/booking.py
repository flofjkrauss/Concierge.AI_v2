"""Booking domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.money import Money
from domain.value_objects.stay_period import StayPeriod


@dataclass(slots=True)
class Booking:
    """A hotel booking."""

    booking_id: str
    customer_id: str
    room_id: str
    stay_period: StayPeriod
    guest_count: int
    total_price: Money    
    status: BookingStatus
    breakfast_included: bool = False
    accessible_requested: bool = False
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.booking_id.strip():
            raise ValueError("booking_id must not be empty")

        if not self.customer_id.strip():
            raise ValueError("customer_id must not be empty")

        if not self.room_id.strip():
            raise ValueError("room_id must not be empty")

        if self.guest_count < 1:
            raise ValueError("guest_count must be at least 1")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")