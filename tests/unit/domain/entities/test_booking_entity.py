from datetime import UTC, datetime
from decimal import Decimal

import pytest

from domain.entities.booking import Booking
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.money import Money
from domain.value_objects.stay_period import StayPeriod


def make_booking(stay_period: StayPeriod, **changes: object) -> Booking:
    values: dict[str, object] = {
        "booking_id": "booking-1",
        "customer_id": "customer-1",
        "room_id": "room-1",
        "stay_period": stay_period,
        "guest_count": 2,
        "total_price": Money(Decimal("200.00"), "EUR"),
        "status": BookingStatus.CONFIRMED,
        "created_at": datetime(2030, 1, 1, tzinfo=UTC),
    }
    values.update(changes)
    return Booking(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["booking_id", "customer_id", "room_id"])
def test_booking_rejects_blank_identifiers(
    stay_period: StayPeriod,
    field: str,
) -> None:
    with pytest.raises(ValueError, match=f"{field} must not be empty"):
        make_booking(stay_period, **{field: "   "})


def test_booking_requires_at_least_one_guest(stay_period: StayPeriod) -> None:
    with pytest.raises(ValueError, match="guest_count must be at least 1"):
        make_booking(stay_period, guest_count=0)


def test_booking_requires_timezone_aware_creation_time(
    stay_period: StayPeriod,
) -> None:
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        make_booking(
            stay_period,
            created_at=datetime(2030, 1, 1, tzinfo=UTC).replace(tzinfo=None),
        )


def test_booking_defaults_to_utc_creation_time(stay_period: StayPeriod) -> None:
    booking = make_booking(stay_period, created_at=datetime.now(UTC))

    assert booking.created_at.tzinfo is not None
