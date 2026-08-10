"""Tests for Streamlit presentation helpers."""

from pathlib import Path

from client.components.models import BookingCardData
from client.components.views import _date_range, _format_money, _room_image_path


def test_room_image_prefers_matching_resource_image(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    resource_dir = tmp_path / "res"
    asset_dir.mkdir()
    resource_dir.mkdir()
    fallback = asset_dir / "room-double.svg"
    preferred = resource_dir / "room-double.png"
    fallback.touch()
    preferred.touch()

    assert _room_image_path(asset_dir, "double") == preferred


def test_room_image_uses_svg_when_resource_image_is_missing(
    tmp_path: Path,
) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    fallback = asset_dir / "room-family.svg"
    fallback.touch()

    assert _room_image_path(asset_dir, "family") == fallback


def test_unknown_room_category_uses_deluxe_svg_fallback(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()

    assert _room_image_path(asset_dir, "penthouse") == (asset_dir / "room-deluxe.svg")


def test_booking_card_normalizes_conversation_booking_shape() -> None:
    booking = BookingCardData.from_mapping(
        {
            "status": "pending",
            "room_category": "double",
            "guest_count": 2,
            "check_in": "2030-06-10",
            "check_out": "2030-06-13",
            "total_prize": {"amount": "405.00", "currency": "EUR"},
            "breakfast": True,
            "accessible": False,
            "first_name": "Alex",
            "last_name": "Morgan",
            "email": "alex@example.com",
        }
    )

    assert booking is not None
    assert booking.guest_name == "Alex Morgan"
    assert booking.guest_count == 2
    assert booking.check_in == "2030-06-10"
    assert booking.total_price == {"amount": "405.00", "currency": "EUR"}
    assert booking.is_cancellation_candidate is False


def test_booking_card_normalizes_api_booking_shape() -> None:
    booking = BookingCardData.from_mapping(
        {
            "booking_id": "booking-1",
            "status": "confirmed",
            "room_category": "family",
            "guest_name": "Sam Harbour",
            "guests": 4,
            "arrival": "2030-07-01",
            "departure": "2030-07-08",
            "total_price": {"amount": 980, "currency": "USD"},
            "breakfast": False,
            "hotel_name": "Harbour Light Hotel",
        }
    )

    assert booking is not None
    assert booking.booking_id == "booking-1"
    assert booking.guest_count == 4
    assert booking.check_out == "2030-07-08"
    assert booking.is_cancellation_candidate is True


def test_booking_card_rejects_unrelated_mapping() -> None:
    assert BookingCardData.from_mapping({"topic": "parking"}) is None


def test_booking_display_helpers_format_dates_and_money() -> None:
    assert _date_range("2030-06-10", "2030-06-13") == (
        "2030-06-10 – 2030-06-13"
    )
    assert _format_money({"amount": "405", "currency": "EUR"}) == "405.00 EUR"
