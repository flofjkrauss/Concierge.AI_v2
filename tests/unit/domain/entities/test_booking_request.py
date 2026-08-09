import pytest

from domain.entities.booking_request import BookingRequest
from domain.value_objects.stay_period import StayPeriod


def test_booking_request_accepts_valid_data(stay_period: StayPeriod) -> None:
    request = BookingRequest("request-1", stay_period, 2, True, True)

    assert request.breakfast_included
    assert request.accessible_requested
    assert "request-1" in str(request)


def test_booking_request_rejects_blank_id(stay_period: StayPeriod) -> None:
    with pytest.raises(ValueError, match="request_id must not be empty"):
        BookingRequest(" ", stay_period, 1)


def test_booking_request_requires_at_least_one_guest(
    stay_period: StayPeriod,
) -> None:
    with pytest.raises(ValueError, match="guest_count must be at least 1"):
        BookingRequest("request-1", stay_period, 0)
