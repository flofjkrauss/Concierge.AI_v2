"""Tests for Streamlit presentation helpers."""

from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pytest

from client.components import views
from client.components.models import BookingCardData, InformationCardData
from client.components.views import (
    _booking_amenities_html,
    _date_range,
    _format_money,
    _render_booking_card,
    _room_details,
    _room_image_path,
    _room_price_html,
    _room_prices,
    render_information_card,
)


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
    assert _format_money({"amount": "405", "currency": "EUR"}) == "405 EUR"
    assert _format_money({"amount": "90.50", "currency": "USD"}) == "$90.5"


def test_room_price_is_separate_from_secondary_details() -> None:
    room: dict[str, object] = {
        "max_occupancy": 2,
        "price_per_night": {"amount": "215", "currency": "EUR"},
        "total_price": {"amount": "645", "currency": "EUR"},
        "breakfast": True,
    }

    nightly, total = _room_prices(room)

    assert (nightly, total) == ("215 EUR", "645 EUR")
    assert _room_details(room) == ["Up to 2 guests", "Breakfast included"]
    price_html = _room_price_html(nightly, total)
    assert "harbour-room-price__amount" in price_html
    assert "215 EUR" in price_html
    assert "645 EUR stay total" in price_html


def test_information_card_normalizes_and_renders_structured_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = {
        "topic": "WiFi",
        "title": "Wi-Fi",
        "answer": " Complimentary Wi-Fi is available throughout the hotel. ",
    }
    information = InformationCardData.from_mapping(data)
    assert information is not None
    assert information.topic == "wifi"
    assert information.answer == "Complimentary Wi-Fi is available throughout the hotel."

    markdown = Mock()
    monkeypatch.setattr(views.st, "markdown", markdown)
    render_information_card(information)

    markup = markdown.call_args.args[0]
    assert "harbour-information-card" in markup
    assert "Wi-Fi" in markup
    assert "Complimentary Wi-Fi is available throughout the hotel." in markup
    assert markdown.call_args.kwargs == {"unsafe_allow_html": True}


def test_information_wire_text_is_rendered_as_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = views.ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "(wifi)Complimentary Wi-Fi is available throughout the hotel.",
        }
    )
    message = views.ChatEntry(
        role="assistant",
        text=response.text,
        response=response,
        message_id="information-1",
    )
    markdown = Mock()
    information_card = Mock()
    monkeypatch.setattr(views, "_svg_data_uri", lambda _: "data:image/svg+xml;base64,")
    monkeypatch.setattr(views.st, "chat_message", lambda *_, **__: nullcontext())
    monkeypatch.setattr(views.st, "markdown", markdown)
    monkeypatch.setattr(views, "render_information_card", information_card)

    views.render_transcript(
        [message],
        asset_dir=Path("assets"),
        session_active=True,
        consumed_actions=set(),
    )

    information_card.assert_called_once_with(
        InformationCardData(
            topic="wifi",
            answer="Complimentary Wi-Fi is available throughout the hotel.",
            title=None,
        )
    )
    markdown.assert_not_called()


@pytest.mark.parametrize(
    "wire_text",
    ["wifi)answer", "(wifi)", "A regular (wifi) message"],
)
def test_information_wire_text_rejects_non_contract_messages(wire_text: str) -> None:
    assert InformationCardData.from_wire_text(wire_text) is None


def test_information_symbols_cover_all_hotel_information_topics() -> None:
    expected_topics = {
        "check_in",
        "check_out",
        "wifi",
        "breakfast",
        "pool",
        "pets",
        "parking",
        "room_categories",
        "location",
        "accessibility",
        "front_desk",
        "early_check_in",
        "late_check_out",
        "restaurant",
        "bar",
        "room_service",
        "ev_charging",
        "service_animals",
        "family_services",
        "smoking",
        "housekeeping",
        "laundry",
        "luggage_storage",
        "payment_methods",
        "cancellation_policy",
        "public_transport",
        "airport_transfer",
        "local_attractions",
        "contact",
    }

    assert set(views.INFORMATION_TOPIC_SYMBOLS) == expected_topics
    assert set(views.INFORMATION_TOPIC_TITLES) == expected_topics


def test_booking_amenities_render_only_requested_icons() -> None:
    booking = _booking_card_data(
        status="pending",
        breakfast=True,
        accessible=True,
    )

    markup = _booking_amenities_html(booking)

    assert 'title="Breakfast requested"' in markup
    assert 'title="Accessible room requested"' in markup
    assert "☕" in markup
    assert "♿" in markup


@pytest.mark.parametrize(
    ("status", "expected_class", "expected_text"),
    [
        ("confirmed", "harbour-booking-card--confirmed", "✓"),
        ("cancelled", "harbour-booking-card--cancelled", "no longer active"),
    ],
)
def test_booking_card_has_explicit_status_treatment(
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    expected_class: str,
    expected_text: str,
) -> None:
    markdown = Mock()
    monkeypatch.setattr(views.st, "markdown", markdown)
    booking = _booking_card_data(
        status=status,
        breakfast=False,
        accessible=False,
    )

    _render_booking_card(
        booking,
        title="Your booking",
        eyebrow="Booking details",
        destructive=status == "cancelled",
    )

    markup = markdown.call_args.args[0]
    assert expected_class in markup
    assert expected_text in markup
    assert "Guest details" in markup
    assert "harbour-booking-card__customer" in markup
    assert markdown.call_args.kwargs == {"unsafe_allow_html": True}


def _booking_card_data(
    *,
    status: str,
    breakfast: bool,
    accessible: bool,
) -> BookingCardData:
    return BookingCardData(
        booking_id=None,
        status=status,
        room_category="deluxe",
        guest_name="Alex Morgan",
        guest_count=2,
        check_in="2030-06-10",
        check_out="2030-06-13",
        total_price={"amount": "645", "currency": "EUR"},
        breakfast=breakfast,
        accessible=accessible,
        email="alex@example.com",
        phone=None,
        hotel_name=None,
        hotel_address=None,
    )
