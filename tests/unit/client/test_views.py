"""Tests for Streamlit presentation helpers."""

from contextlib import nullcontext
from html import escape
from pathlib import Path
from unittest.mock import Mock

import pytest

from client.components import views
from client.components.models import BookingCardData, InformationCardData
from client.components.views import (
    _booking_amenities_html,
    _booking_customer_html,
    _booking_fact,
    _date_range,
    _format_money,
    _optional_line,
    _render_booking_card,
    _render_booking_details,
    _render_confirmation,
    _render_room_cards,
    _room_details,
    _room_image_path,
    _room_price_html,
    _room_prices,
    _svg_data_uri,
    apply_theme,
    render_header,
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
    grouped_topics = {
        topic
        for _, topics in views.INFORMATION_TOPIC_GROUPS
        for topic in topics
    }
    assert grouped_topics == expected_topics


def test_available_information_topics_render_as_grouped_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    markdown = Mock()
    monkeypatch.setattr(views.st, "markdown", markdown)

    render_information_card(
        InformationCardData(
            topic="available_topics",
            answer="Available hotel information topics",
            title=None,
        )
    )

    markup = markdown.call_args.args[0]
    assert "harbour-information-topics-card" in markup
    assert "What can I help with?" in markup
    for group_title, _ in views.INFORMATION_TOPIC_GROUPS:
        assert escape(group_title) in markup
    for topic_title in views.INFORMATION_TOPIC_TITLES.values():
        assert topic_title in markup
    assert markdown.call_args.kwargs == {"unsafe_allow_html": True}


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


def test_apply_theme_embeds_local_assets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    theme = tmp_path / "theme.css"
    background = tmp_path / "background.png"
    pattern = tmp_path / "pattern.svg"
    theme.write_text(
        "a{background:__HARBOUR_BACKGROUND__}b{background:__HARBOUR_CHROME_PATTERN__}",
        encoding="utf-8",
    )
    background.write_bytes(b"background")
    pattern.write_bytes(b"pattern")
    html = Mock()
    monkeypatch.setattr(views.st, "html", html)

    apply_theme(theme, background, pattern)

    markup = html.call_args.args[0]
    assert "__HARBOUR_BACKGROUND__" not in markup
    assert "__HARBOUR_CHROME_PATTERN__" not in markup
    assert "data:image/png;base64," in markup
    assert "data:image/svg+xml;base64," in markup


def test_render_header_embeds_logo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    logo = tmp_path / "logo.svg"
    logo.write_text("<svg></svg>", encoding="utf-8")
    markdown = Mock()
    monkeypatch.setattr(views.st, "container", lambda **_: nullcontext())
    monkeypatch.setattr(views.st, "markdown", markdown)

    render_header(logo)

    markup = markdown.call_args.args[0]
    assert "Harbour Light Hotel" in markup
    assert _svg_data_uri(logo) in markup
    assert markdown.call_args.kwargs == {"unsafe_allow_html": True}


def test_room_cards_return_valid_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response = views.ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Rooms found",
            "content": {
                "rooms": [
                    {
                        "category": "double",
                        "description": " Harbour view ",
                        "max_occupancy": 2,
                        "price_per_night": {"amount": "150", "currency": "EUR"},
                        "accessible": True,
                    }
                ],
                "request": {
                    "check_in": "2030-06-10",
                    "check_out": "2030-06-13",
                    "guest_count": 2,
                    "accessible": True,
                },
            },
        }
    )
    monkeypatch.setattr(views.st, "container", lambda **_: nullcontext())
    monkeypatch.setattr(views.st, "columns", lambda *_, **__: [nullcontext()])
    monkeypatch.setattr(views.st, "button", Mock(return_value=True))
    monkeypatch.setattr(views.st, "image", Mock())
    monkeypatch.setattr(views.st, "markdown", Mock())
    monkeypatch.setattr(views.st, "write", Mock())
    monkeypatch.setattr(views.st, "caption", Mock())
    monkeypatch.setattr(views, "_room_image_path", lambda *_: tmp_path / "room.svg")

    selected = _render_room_cards(
        response,
        message_id="rooms-1",
        asset_dir=tmp_path,
        actionable=True,
    )

    assert selected is not None
    assert selected.visible_text == "Select Double Room"
    assert selected.source_message_id == "rooms-1"
    assert selected.api_text.startswith("__concierge_booking_selection_v1__|")
    views.st.write.assert_called_once_with("Harbour view")
    views.st.caption.assert_called_once_with("Up to 2 guests · Accessible")


def test_room_cards_ignore_missing_rooms_or_invalid_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    empty = views.ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "No rooms",
            "content": {"rooms": []},
        }
    )
    assert (
        _render_room_cards(
            empty,
            message_id="empty",
            asset_dir=tmp_path,
            actionable=True,
        )
        is None
    )

    invalid_request = views.ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Rooms",
            "content": {"rooms": [{"category": "single"}], "request": {}},
        }
    )
    button = Mock(return_value=True)
    monkeypatch.setattr(views.st, "container", lambda **_: nullcontext())
    monkeypatch.setattr(views.st, "columns", lambda *_, **__: [nullcontext()])
    monkeypatch.setattr(views.st, "button", button)
    monkeypatch.setattr(views.st, "image", Mock())
    monkeypatch.setattr(views.st, "markdown", Mock())
    monkeypatch.setattr(views, "_room_image_path", lambda *_: tmp_path / "room.svg")

    assert (
        _render_room_cards(
            invalid_request,
            message_id="invalid",
            asset_dir=tmp_path,
            actionable=True,
        )
        is None
    )
    assert button.call_args.kwargs["disabled"] is True


@pytest.mark.parametrize(
    ("booking_status", "clicked", "visible_text", "api_text"),
    [
        ("pending", [True, False], "Book this room", "confirm"),
        ("confirmed", [False, True], "Keep my booking", "decline"),
    ],
)
def test_confirmation_buttons_return_guest_shortcuts(
    monkeypatch: pytest.MonkeyPatch,
    booking_status: str,
    clicked: list[bool],
    visible_text: str,
    api_text: str,
) -> None:
    response = views.ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Please confirm",
            "data": {
                "status": booking_status,
                "room_category": "double",
                "check_in": "2030-06-10",
                "check_out": "2030-06-13",
            },
        }
    )
    monkeypatch.setattr(
        views.st,
        "columns",
        lambda *_, **__: [nullcontext(), nullcontext()],
    )
    monkeypatch.setattr(views.st, "button", Mock(side_effect=clicked))
    render_card = Mock()
    monkeypatch.setattr(views, "_render_booking_card", render_card)

    selected = _render_confirmation(
        response,
        message_id="confirmation-1",
        actionable=True,
    )

    assert selected is not None
    assert (selected.visible_text, selected.api_text) == (visible_text, api_text)
    assert selected.source_message_id == "confirmation-1"
    assert render_card.call_args.kwargs["destructive"] is (
        booking_status == "confirmed"
    )


def test_booking_details_render_only_valid_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    render_card = Mock()
    monkeypatch.setattr(views, "_render_booking_card", render_card)
    message = views.ConversationResponse.from_payload(
        {"session_active": True, "text": "No details"}
    )
    _render_booking_details(message)
    render_card.assert_not_called()

    cancelled = views.ConversationResponse.from_payload(
        {
            "session_active": True,
            "text": "Cancelled",
            "content": {
                "booking_id": "booking-1",
                "status": "cancelled",
                "room_category": "double",
            },
        }
    )
    _render_booking_details(cancelled)

    assert render_card.call_args.kwargs == {
        "title": "Cancelled booking",
        "eyebrow": "Cancellation complete",
        "destructive": True,
    }


def test_optional_booking_markup_escapes_guest_content() -> None:
    assert _booking_fact("Guest", None) == ""
    assert "&lt;Alex&gt;" in _booking_fact("Guest", "<Alex>")
    assert _optional_line(None, "detail") == ""
    assert "&lt;Hotel&gt;" in _optional_line("<Hotel>", "detail")
    assert _booking_customer_html([]) == ""
    assert "alex&amp;sam@example.com" in _booking_customer_html(
        ["alex&sam@example.com"]
    )


@pytest.mark.parametrize(
    "value",
    [None, {}, {"amount": [], "currency": "EUR"}, {"amount": "x", "currency": "EUR"}],
)
def test_format_money_rejects_invalid_values(value: object) -> None:
    assert _format_money(value) is None
