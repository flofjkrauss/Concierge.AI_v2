"""Reusable Streamlit presentation components for guest interactions."""

from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path

import streamlit as st

from client.components.api import ConversationResponse, ResponseKind
from client.components.models import (
    AvailabilitySelectionData,
    BookingCardData,
    ChatEntry,
    InformationCardData,
    Shortcut,
)
from conversation.value_object.default_phrases import INFORMATION_TOPICS_WIRE_TOPIC
from conversation.value_object.information_topic_selection import (
    InformationTopicSelection,
)
from domain.value_objects.information_topic import InformationTopic

CATEGORY_LABELS = {
    "single": "Single Room",
    "double": "Double Room",
    "deluxe": "Deluxe Room",
    "family": "Family Room",
}
CATEGORY_IMAGES: dict[str, str] = {}
for category in CATEGORY_LABELS:
    CATEGORY_IMAGES[category] = f"room-{category}.svg"

ROOM_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".svg")
INFORMATION_TOPIC_SYMBOLS = {
    "check_in": "↘",
    "check_out": "↗",
    "wifi": "📶",
    "breakfast": "☕",
    "pool": "≈",
    "pets": "🐾",
    "parking": "P",
    "room_categories": "▦",
    "location": "⌖",
    "accessibility": "♿",
    "front_desk": "☎",
    "early_check_in": "◷",
    "late_check_out": "◴",
    "restaurant": "♨",
    "bar": "◇",
    "room_service": "▤",
    "ev_charging": "⚡",
    "service_animals": "♙",
    "family_services": "♟",
    "smoking": "⊘",
    "housekeeping": "✦",
    "laundry": "◌",
    "luggage_storage": "▣",
    "payment_methods": "▱",
    "cancellation_policy": "✕",
    "public_transport": "▰",
    "airport_transfer": "✈",
    "local_attractions": "★",
    "contact": "✉",
}
INFORMATION_TOPIC_TITLES = {
    "check_in": "Check-in time",
    "check_out": "Check-out time",
    "wifi": "Wi-Fi",
    "breakfast": "Breakfast service",
    "pool": "Pool",
    "pets": "Pet policy",
    "parking": "Guest parking",
    "room_categories": "Room categories",
    "location": "Hotel location",
    "accessibility": "Accessibility",
    "front_desk": "Front desk hours",
    "early_check_in": "Early check-in",
    "late_check_out": "Late check-out",
    "restaurant": "Restaurant",
    "bar": "Hotel bar",
    "room_service": "Room service",
    "ev_charging": "Electric vehicle charging",
    "service_animals": "Service animals",
    "family_services": "Family services",
    "smoking": "Smoking policy",
    "housekeeping": "Housekeeping",
    "laundry": "Laundry service",
    "luggage_storage": "Luggage storage",
    "payment_methods": "Accepted payment methods",
    "cancellation_policy": "Standard cancellation policy",
    "public_transport": "Public transport",
    "airport_transfer": "Airport transfer",
    "local_attractions": "Nearby attractions",
    "contact": "Hotel contact",
}
INFORMATION_TOPIC_ALIASES = {
    "accessability": "accessibility",
    "late_check_in": "late_check_out",
}
INFORMATION_TOPIC_GROUPS = (
    (
        "Stay & arrival",
        (
            "check_in",
            "check_out",
            "early_check_in",
            "late_check_out",
            "luggage_storage",
        ),
    ),
    (
        "Rooms & guest needs",
        (
            "room_categories",
            "accessibility",
            "family_services",
            "service_animals",
            "smoking",
            "housekeeping",
            "laundry",
        ),
    ),
    (
        "Food & leisure",
        ("breakfast", "restaurant", "bar", "room_service", "pool"),
    ),
    (
        "Travel & connectivity",
        (
            "wifi",
            "parking",
            "ev_charging",
            "public_transport",
            "airport_transfer",
            "location",
        ),
    ),
    (
        "Policies & local help",
        (
            "payment_methods",
            "cancellation_policy",
            "pets",
            "local_attractions",
            "front_desk",
            "contact",
        ),
    ),
)


def apply_theme(
    theme_path: Path,
    background_path: Path,
    chrome_pattern_path: Path,
) -> None:
    """Load the local, self-contained visual theme."""

    background = base64.b64encode(background_path.read_bytes()).decode("ascii")
    chrome_pattern = base64.b64encode(chrome_pattern_path.read_bytes()).decode("ascii")
    stylesheet = theme_path.read_text(encoding="utf-8")
    stylesheet = stylesheet.replace(
        "__HARBOUR_BACKGROUND__", f"data:image/png;base64,{background}"
    ).replace(
        "__HARBOUR_CHROME_PATTERN__",
        f"data:image/svg+xml;base64,{chrome_pattern}",
    )
    st.html(f"<style>{stylesheet}</style>")


def render_header(logo_path: Path) -> None:
    """Render compact hotel branding."""

    with st.container(key="hotel_header"):
        st.markdown(
            (
                '<div class="harbour-header-content">'
                '<div class="harbour-brand">'
                f'<img src="{_svg_data_uri(logo_path)}" '
                'alt="Harbour Light Hotel">'
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def render_transcript(
    messages: list[ChatEntry],
    *,
    asset_dir: Path,
    actions_enabled: bool,
    consumed_actions: set[str],
) -> Shortcut | None:
    """Render messages and return at most one selected shortcut."""

    selected: Shortcut | None = None
    assistant_avatar = _svg_data_uri(asset_dir / "harbour-light-mark.svg")
    guest_avatar = _svg_data_uri(asset_dir / "guest-avatar.svg")
    latest_message_id = None
    if messages:
        latest_message_id = messages[-1].message_id

    for entry in messages:
        avatar = guest_avatar
        if entry.role == "assistant":
            avatar = assistant_avatar

        with st.chat_message(entry.role, avatar=avatar):
            response = entry.response
            information = None
            if (
                entry.role == "assistant"
                and response is not None
                and response.kind is ResponseKind.MESSAGE
            ):
                information = InformationCardData.from_wire_text(entry.text)

            if information is not None:
                action = render_information_card(
                    information,
                    message_id=entry.message_id,
                    actionable=actions_enabled,
                )
                selected = selected or action
            else:
                st.markdown(entry.text)
            if response is None:
                continue

            unconsumed = actions_enabled and entry.message_id not in consumed_actions
            actionable = unconsumed and (
                response.kind is ResponseKind.AVAILABILITY
                or entry.message_id == latest_message_id
            )
            action = _render_structured_response(
                response,
                message_id=entry.message_id,
                asset_dir=asset_dir,
                actionable=actionable,
            )
            selected = selected or action
    return selected


def _render_structured_response(
    response: ConversationResponse,
    *,
    message_id: str,
    asset_dir: Path,
    actionable: bool,
) -> Shortcut | None:
    if response.kind is ResponseKind.AVAILABILITY:
        return _render_room_cards(
            response,
            message_id=message_id,
            asset_dir=asset_dir,
            actionable=actionable,
        )
    if response.kind is ResponseKind.CONFIRMATION:
        return _render_confirmation(
            response,
            message_id=message_id,
            actionable=actionable,
        )
    if response.kind is ResponseKind.BOOKING:
        _render_booking_details(response)
    return None


def render_information_card(
    information: InformationCardData,
    *,
    message_id: str | None = None,
    actionable: bool = False,
) -> Shortcut | None:
    """Render one hotel-information answer from the conversation API."""

    topic = INFORMATION_TOPIC_ALIASES.get(information.topic, information.topic)
    if topic == INFORMATION_TOPICS_WIRE_TOPIC:
        return _render_information_topics_card(
            information,
            message_id=message_id or "information-topics",
            actionable=actionable and message_id is not None,
        )

    symbol = INFORMATION_TOPIC_SYMBOLS.get(topic, "i")
    title = (
        information.title
        or INFORMATION_TOPIC_TITLES.get(topic)
        or topic.replace("_", " ").title()
    )
    markup = (
        '<section class="harbour-information-card" '
        f'aria-label="Hotel information: {escape(title)}">'
        '<span class="harbour-information-card__icon" aria-hidden="true">'
        f"{escape(symbol)}"
        "</span>"
        '<div class="harbour-information-card__content">'
        '<span class="harbour-information-card__eyebrow">Hotel information</span>'
        f"<h4>{escape(title)}</h4>"
        f"<p>{escape(information.answer)}</p>"
        "</div>"
        "</section>"
    )
    st.markdown(markup, unsafe_allow_html=True)
    return None


def _render_information_topics_card(
    information: InformationCardData,
    *,
    message_id: str,
    actionable: bool,
) -> Shortcut | None:
    """Render the complete hotel-information topic guide."""

    title = information.title or "What can I help with?"
    header = (
        '<header class="harbour-information-topics-card__header" '
        f'aria-label="Hotel information: {escape(title)}">'
        '<span class="harbour-information-card__icon" aria-hidden="true">i</span>'
        '<div class="harbour-information-card__content">'
        '<span class="harbour-information-card__eyebrow">Hotel information</span>'
        f"<h4>{escape(title)}</h4>"
        "<p>Select a topic to see the hotel information.</p>"
        "</div>"
        "</header>"
    )
    action_key = f"information_topic_action_{message_id}"

    with st.container(key=f"information_topics_card_{message_id}"):
        st.markdown(header, unsafe_allow_html=True)
        columns = st.columns(2, gap="small")
        for index, (group_title, topics) in enumerate(INFORMATION_TOPIC_GROUPS):
            with (
                columns[index % len(columns)],
                st.container(key=f"information_topic_group_{message_id}_{index}"),
            ):
                st.markdown(f"##### {group_title}")
                selection_key = f"information_topic_{message_id}_{index}"
                st.pills(
                    group_title,
                    options=topics,
                    format_func=_information_topic_label,
                    key=selection_key,
                    on_change=_queue_information_topic,
                    args=(selection_key, action_key),
                    disabled=not actionable,
                    label_visibility="collapsed",
                    width="stretch",
                )

    selected_topic = st.session_state.pop(action_key, None)

    if (
        not actionable
        or not isinstance(selected_topic, str)
        or selected_topic not in INFORMATION_TOPIC_TITLES
    ):
        return None

    title = INFORMATION_TOPIC_TITLES[selected_topic]
    # Topic cards stay reusable, so their actions are never marked consumed.
    return Shortcut(
        visible_text=f"Tell me about {title}",
        api_text=InformationTopicSelection(InformationTopic(selected_topic)).to_wire(),
        source_message_id=None,
    )


def _information_topic_label(topic: str) -> str:
    return f"{INFORMATION_TOPIC_SYMBOLS[topic]}  {INFORMATION_TOPIC_TITLES[topic]}"


def _queue_information_topic(selection_key: str, action_key: str) -> None:
    """Queue one chip click and clear its selection for repeat clicks."""

    selection = st.session_state.get(selection_key)
    if not isinstance(selection, str):
        return
    st.session_state[action_key] = selection
    st.session_state[selection_key] = None


def _render_room_cards(
    response: ConversationResponse,
    *,
    message_id: str,
    asset_dir: Path,
    actionable: bool,
) -> Shortcut | None:
    rooms = response.rooms()
    if not rooms:
        return None

    raw_request = response.availability_request()
    request = None
    if raw_request is not None:
        request = AvailabilitySelectionData.from_mapping(raw_request)

    selected: Shortcut | None = None
    with st.container(key=f"room_grid_{message_id}"):
        columns = st.columns(len(rooms), gap="small")
        for column, room in zip(columns, rooms, strict=True):
            category = str(room.get("category", "room")).casefold()
            label = CATEGORY_LABELS.get(
                category,
                category.replace("_", " ").title(),
            )
            with (
                column,
                st.container(
                    border=True,
                    key=f"room_card_{message_id}_{category}",
                ),
            ):
                st.image(
                    str(_room_image_path(asset_dir, category)),
                    width="stretch",
                )
                st.markdown(f"#### {label}")
                description = room.get("description")
                if isinstance(description, str) and description.strip():
                    st.write(description.strip())
                nightly_price, stay_total = _room_prices(room)
                if nightly_price is not None or stay_total is not None:
                    st.markdown(
                        _room_price_html(nightly_price, stay_total),
                        unsafe_allow_html=True,
                    )
                details = _room_details(room)
                if details:
                    st.caption(" · ".join(details))
                if st.button(
                    f"Select {label}",
                    key=f"select_{message_id}_{category}",
                    type="primary",
                    disabled=not actionable or request is None,
                    width="stretch",
                ):
                    if request is None:
                        continue
                    selected = Shortcut(
                        visible_text=f"Select {label}",
                        api_text=request.booking_message(category),
                        source_message_id=message_id,
                    )
    return selected


def _room_details(room: dict[str, object]) -> list[str]:
    details: list[str] = []
    occupancy = room.get("max_occupancy")
    if isinstance(occupancy, int):
        guest_label = "guests"
        if occupancy == 1:
            guest_label = "guest"
        details.append(f"Up to {occupancy} {guest_label}")

    if room.get("breakfast_included") is True or room.get("breakfast") is True:
        details.append("Breakfast included")
    if room.get("is_accessible") is True or room.get("accessible") is True:
        details.append("Accessible")
    return details


def _room_prices(room: dict[str, object]) -> tuple[str | None, str | None]:
    nightly_price = _format_money(room.get("price_per_night"))
    stay_total = _format_money(room.get("total_price")) or _format_money(
        room.get("total_stay_price")
    )
    return nightly_price, stay_total


def _room_price_html(nightly_price: str | None, stay_total: str | None) -> str:
    primary_price = nightly_price or stay_total
    if primary_price is None:
        return ""
    primary_label = "Stay total"
    if nightly_price is not None:
        primary_label = "Nightly rate"

    suffix = '<span class="harbour-room-price__suffix">per night</span>'
    if nightly_price is None:
        suffix = ""
    total_line = ""
    if nightly_price is not None and stay_total is not None:
        total_line = (
            '<span class="harbour-room-price__total">'
            f"{escape(stay_total)} stay total"
            "</span>"
        )
    return (
        '<div class="harbour-room-price">'
        f'<span class="harbour-room-price__label">{primary_label}</span>'
        '<div class="harbour-room-price__amount">'
        f"<strong>{escape(primary_price)}</strong>"
        f"{suffix}"
        "</div>"
        f"{total_line}"
        "</div>"
    )


def _room_image_path(asset_dir: Path, category: str) -> Path:
    """Prefer a category image from ``res`` and retain the SVG fallback."""

    resource_dir = asset_dir.parent / "res"
    image_stem = f"room-{category}"
    for suffix in ROOM_IMAGE_SUFFIXES:
        candidate = resource_dir / f"{image_stem}{suffix}"
        if candidate.is_file():
            return candidate

    fallback_name = CATEGORY_IMAGES.get(category, "room-deluxe.svg")
    return asset_dir / fallback_name


def _render_confirmation(
    response: ConversationResponse,
    *,
    message_id: str,
    actionable: bool,
) -> Shortcut | None:
    data = response.structured_data("data") or {}
    booking = BookingCardData.from_mapping(data)
    destructive = booking is not None and booking.is_cancellation_candidate
    if booking is not None:
        booking_title = "Booking preview"
        booking_eyebrow = "Ready to confirm"
        if destructive:
            booking_title = "Booking to cancel"
            booking_eyebrow = "Please review"

        _render_booking_card(
            booking,
            title=booking_title,
            eyebrow=booking_eyebrow,
            destructive=destructive,
        )

    primary_label = "Book room"
    secondary_label = "Not now"
    primary_visible = "Book this room"
    secondary_visible = "Not now"
    primary_key_prefix = "book_room"
    primary_type = "primary"
    if destructive:
        primary_label = "Cancel booking"
        secondary_label = "Keep booking"
        primary_visible = "Cancel this booking"
        secondary_visible = "Keep my booking"
        primary_key_prefix = "cancel_booking"
        primary_type = "secondary"

    primary_column, secondary_column = st.columns(2, gap="small")
    with primary_column:
        clicked_primary = st.button(
            primary_label,
            key=f"{primary_key_prefix}_{message_id}",
            type=primary_type,
            disabled=not actionable,
            width="stretch",
        )
    with secondary_column:
        clicked_secondary = st.button(
            secondary_label,
            key=f"confirmation_decline_{message_id}",
            type="secondary",
            disabled=not actionable,
            width="stretch",
        )

    if clicked_primary:
        return Shortcut(primary_visible, "confirm", message_id)
    if clicked_secondary:
        return Shortcut(secondary_visible, "decline", message_id)
    return None


def _render_booking_details(response: ConversationResponse) -> None:
    content = response.structured_data("content")
    if content is None:
        return
    booking = BookingCardData.from_mapping(content)
    if booking is None:
        return
    cancelled = booking.status == "cancelled"
    title = "Your booking"
    eyebrow = "Booking details"
    if cancelled:
        title = "Cancelled booking"
        eyebrow = "Cancellation complete"

    _render_booking_card(
        booking,
        title=title,
        eyebrow=eyebrow,
        destructive=cancelled,
    )


def _render_booking_card(
    booking: BookingCardData,
    *,
    title: str,
    eyebrow: str,
    destructive: bool,
) -> None:
    """Render the shared booking summary used throughout the conversation."""

    status_key = (booking.status or "pending").casefold()
    status = status_key.replace("_", " ").title()
    category = booking.room_category or "room"
    room_label = CATEGORY_LABELS.get(
        category.casefold(),
        category.replace("_", " ").title(),
    )
    dates = _date_range(booking.check_in, booking.check_out)
    total = _format_money(booking.total_price)
    guest_count = None
    if booking.guest_count is not None:
        guest_label = "guests"
        if booking.guest_count == 1:
            guest_label = "guest"
        guest_count = f"{booking.guest_count} {guest_label}"

    facts = [
        _booking_fact("Stay", dates),
        _booking_fact("Guests", guest_count),
        _booking_fact("Total", total),
    ]
    contact_parts: list[str] = []
    for part in (booking.guest_name, booking.email, booking.phone):
        if part:
            contact_parts.append(part)

    hotel_parts: list[str] = []
    for part in (booking.hotel_name, booking.hotel_address):
        if part:
            hotel_parts.append(part)

    reference = None
    if booking.booking_id:
        reference = f"Reference {booking.booking_id}"

    modifiers: list[str] = []
    if destructive:
        modifiers.append("harbour-booking-card--danger")
    if status_key == "confirmed":
        modifiers.append("harbour-booking-card--confirmed")
    if status_key == "cancelled":
        modifiers.append("harbour-booking-card--cancelled")

    modifier_parts: list[str] = []
    for name in modifiers:
        modifier_parts.append(f" {name}")
    modifier = "".join(modifier_parts)

    visible_facts: list[str] = []
    for fact in facts:
        if fact:
            visible_facts.append(fact)
    facts_html = "".join(visible_facts)

    amenities_html = _booking_amenities_html(booking)
    contact_html = _booking_customer_html(contact_parts)
    hotel_line = None
    if hotel_parts:
        hotel_line = " · ".join(hotel_parts)
    hotel_html = _optional_line(
        hotel_line,
        "harbour-booking-card__hotel",
    )
    status_symbol = {"confirmed": "✓", "cancelled": "✕", "pending": "◷"}.get(
        status_key,
        "•",
    )
    cancelled_notice = ""
    if status_key == "cancelled":
        cancelled_notice = (
            '<p class="harbour-booking-card__cancelled-notice">'
            '<span aria-hidden="true">✕</span>'
            "This booking has been cancelled and is no longer active."
            "</p>"
        )
    card = (
        f'<section class="harbour-booking-card{modifier}" '
        f'aria-label="{escape(title)}: {escape(status)}">'
        '<div class="harbour-booking-card__header">'
        "<div>"
        f'<span class="harbour-booking-card__eyebrow">{escape(eyebrow)}</span>'
        f"<h4>{escape(title)}</h4>"
        "</div>"
        '<span class="harbour-booking-card__status">'
        f'<span aria-hidden="true">{status_symbol}</span>{escape(status)}'
        "</span>"
        "</div>"
        '<div class="harbour-booking-card__room">'
        '<span class="harbour-booking-card__anchor" aria-hidden="true">✦</span>'
        '<div class="harbour-booking-card__room-copy">'
        '<div class="harbour-booking-card__room-title">'
        f"<strong>{escape(room_label)}</strong>{amenities_html}"
        "</div>"
        f"{_optional_line(reference, 'harbour-booking-card__reference')}"
        "</div>"
        "</div>"
        f'<dl class="harbour-booking-card__facts">{facts_html}</dl>'
        f"{cancelled_notice}"
        f"{contact_html}"
        f"{hotel_html}"
        "</section>"
    )
    st.markdown(card, unsafe_allow_html=True)


def _booking_amenities_html(
    booking: BookingCardData,
) -> str:
    icons: list[str] = []
    if booking.breakfast is True:
        icons.append(
            _amenity_icon(
                symbol="☕︎",
                label="Breakfast requested",
            )
        )
    if booking.accessible is True:
        icons.append(
            _amenity_icon(
                symbol="♿︎",
                label="Accessible room requested",
            )
        )
    if not icons:
        return ""
    return (
        '<span class="harbour-booking-card__amenities" '
        'aria-label="Requested amenities">'
        f"{''.join(icons)}"
        "</span>"
    )


def _amenity_icon(*, symbol: str, label: str) -> str:
    return (
        '<span class="harbour-booking-card__amenity" role="img" tabindex="0" '
        f'aria-label="{escape(label)}" title="{escape(label)}">'
        f'<span aria-hidden="true">{escape(symbol)}</span>'
        "</span>"
    )


def _date_range(check_in: str | None, check_out: str | None) -> str | None:
    if check_in is not None and check_out is not None:
        return f"{check_in} – {check_out}"
    return check_in or check_out


def _booking_fact(label: str, value: str | None) -> str:
    if value is None:
        return ""
    return f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>"


def _optional_line(value: str | None, class_name: str) -> str:
    if value is None:
        return ""
    return f'<p class="{class_name}">{escape(value)}</p>'


def _booking_customer_html(contact_parts: list[str]) -> str:
    if not contact_parts:
        return ""
    details = " · ".join(contact_parts)
    return (
        '<div class="harbour-booking-card__customer">'
        '<span class="harbour-booking-card__customer-label">Guest details</span>'
        f"<p>{escape(details)}</p>"
        "</div>"
    )


def _format_money(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    amount = value.get("amount")
    currency = value.get("currency")
    if not isinstance(amount, (int, float, str)) or not isinstance(currency, str):
        return None
    try:
        decimal_amount = Decimal(str(amount))
    except InvalidOperation:
        return None
    normalized = decimal_amount.quantize(Decimal("0.01"))
    if normalized == normalized.to_integral_value():
        formatted = f"{normalized:,.0f}"
    else:
        formatted = f"{normalized:,.2f}".rstrip("0").rstrip(".")
    if currency.upper() == "USD":
        return f"${formatted}"
    return f"{formatted} {currency}"


def _svg_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
