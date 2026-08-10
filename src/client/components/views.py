"""Reusable Streamlit presentation components for guest interactions."""

from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st

from client.components.api import ConversationResponse, ResponseKind
from client.components.models import ChatEntry, Shortcut

CATEGORY_LABELS = {
    "single": "Single Room",
    "double": "Double Room",
    "deluxe": "Deluxe Room",
    "family": "Family Room",
}
CATEGORY_IMAGES = {category: f"room-{category}.svg" for category in CATEGORY_LABELS}
ROOM_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".svg")


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
    session_active: bool,
    consumed_actions: set[str],
) -> Shortcut | None:
    """Render messages and return at most one selected shortcut."""

    selected: Shortcut | None = None
    assistant_avatar = _svg_data_uri(asset_dir / "harbour-light-mark.svg")
    guest_avatar = _svg_data_uri(asset_dir / "guest-avatar.svg")
    latest_message_id = messages[-1].message_id if messages else None

    for entry in messages:
        avatar = assistant_avatar if entry.role == "assistant" else guest_avatar
        with st.chat_message(entry.role, avatar=avatar):
            st.write(entry.text)
            response = entry.response
            if response is None:
                continue

            actionable = (
                session_active
                and entry.message_id == latest_message_id
                and entry.message_id not in consumed_actions
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
                details = _room_details(room)
                if details:
                    st.caption(" · ".join(details))
                if st.button(
                    f"Select {label}",
                    key=f"select_{message_id}_{category}",
                    type="primary",
                    disabled=not actionable,
                    width="stretch",
                ):
                    selected = Shortcut(
                        visible_text=f"Select {label}",
                        api_text=f"I would like to book the {label}.",
                        source_message_id=message_id,
                    )
    return selected


def _room_details(room: dict[str, object]) -> list[str]:
    details: list[str] = []
    occupancy = room.get("max_occupancy")
    if isinstance(occupancy, int):
        guest_label = "guest" if occupancy == 1 else "guests"
        details.append(f"Up to {occupancy} {guest_label}")

    price = _format_money(room.get("price_per_night"))
    if price is not None:
        details.append(f"{price} per night")

    total = _format_money(room.get("total_price")) or _format_money(
        room.get("total_stay_price")
    )
    if total is not None:
        details.append(f"{total} stay total")

    if room.get("breakfast_included") is True or room.get("breakfast") is True:
        details.append("Breakfast included")
    if room.get("is_accessible") is True or room.get("accessible") is True:
        details.append("Accessible")
    return details


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
    _render_confirmation_summary(data)
    destructive = isinstance(data.get("booking_id"), str)

    primary_label = "Cancel booking" if destructive else "Book room"
    secondary_label = "Keep booking" if destructive else "Not now"
    primary_visible = "Cancel this booking" if destructive else "Book this room"
    secondary_visible = "Keep my booking" if destructive else "Not now"

    primary_column, secondary_column = st.columns(2, gap="small")
    with primary_column:
        clicked_primary = st.button(
            primary_label,
            key=f"{'cancel_booking' if destructive else 'book_room'}_{message_id}",
            type="secondary" if destructive else "primary",
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


def _render_confirmation_summary(data: dict[str, object]) -> None:
    category = _information_value(data, "room_category")
    check_in = _information_value(data, "check_in")
    check_out = _information_value(data, "check_out")
    guests = _information_value(data, "guest_count")

    summary: list[str] = []
    if isinstance(category, str):
        summary.append(CATEGORY_LABELS.get(category, category.title()))
    if isinstance(check_in, str) and isinstance(check_out, str):
        summary.append(f"{check_in} to {check_out}")
    if isinstance(guests, int):
        summary.append(f"{guests} {'guest' if guests == 1 else 'guests'}")
    if summary:
        st.caption(" · ".join(summary))


def _render_booking_details(response: ConversationResponse) -> None:
    content = response.structured_data("content")
    if content is None:
        return

    category = content.get("room_category")
    arrival = content.get("arrival")
    departure = content.get("departure")
    guests = content.get("guests")
    total = _format_money(content.get("total_price"))

    details: list[str] = []
    if isinstance(category, str):
        details.append(CATEGORY_LABELS.get(category, category.title()))
    if isinstance(arrival, str) and isinstance(departure, str):
        details.append(f"{arrival} to {departure}")
    if isinstance(guests, int):
        details.append(f"{guests} {'guest' if guests == 1 else 'guests'}")
    if total is not None:
        details.append(f"{total} total")
    if details:
        st.caption(" · ".join(details))


def _information_value(data: dict[str, object], key: str) -> object | None:
    value = data.get(key)
    if isinstance(value, dict):
        return value.get("content")
    return value


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
    formatted = f"{decimal_amount:,.2f}"
    if currency.upper() == "USD":
        return f"${formatted}"
    return f"{formatted} {currency}"


def _svg_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
