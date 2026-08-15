"""Tests for immutable Streamlit client view models."""

import pytest

from client.components.models import (
    AvailabilitySelectionData,
    BookingCardData,
    ChatEntry,
    InformationCardData,
)
from conversation.value_object.booking_selection import BookingSelection
from domain.value_objects.room_category import RoomCategory


def test_chat_entry_generates_distinct_message_ids() -> None:
    first = ChatEntry("user", "Hello")
    second = ChatEntry("user", "Hello")

    assert first.message_id
    assert first.message_id != second.message_id


def test_availability_selection_validates_and_builds_booking_wire_message() -> None:
    selection = AvailabilitySelectionData.from_mapping(
        {
            "check_in": "2030-06-10",
            "check_out": "2030-06-13",
            "guest_count": 2,
            "accessible": True,
        }
    )

    assert selection is not None
    parsed = BookingSelection.from_wire(selection.booking_message("double"))
    assert parsed is not None
    assert parsed.room_category is RoomCategory.DOUBLE
    assert parsed.guest_count == 2
    assert parsed.accessible is True


@pytest.mark.parametrize(
    "mapping",
    [
        {},
        {
            "check_in": "invalid",
            "check_out": "2030-06-13",
            "guest_count": 2,
            "accessible": False,
        },
        {
            "check_in": "2030-06-13",
            "check_out": "2030-06-10",
            "guest_count": 2,
            "accessible": False,
        },
        {
            "check_in": "2030-06-10",
            "check_out": "2030-06-13",
            "guest_count": True,
            "accessible": False,
        },
    ],
)
def test_availability_selection_rejects_invalid_mappings(
    mapping: dict[str, object],
) -> None:
    assert AvailabilitySelectionData.from_mapping(mapping) is None


def test_information_card_normalizes_mapping_and_nested_content() -> None:
    result = InformationCardData.from_mapping(
        {
            "topic": {"content": "WiFi"},
            "answer": " Complimentary access ",
            "title": " Wireless internet ",
        }
    )

    assert result == InformationCardData(
        topic="wifi",
        answer="Complimentary access",
        title="Wireless internet",
    )
    assert InformationCardData.from_mapping({"topic": "wifi"}) is None


def test_booking_card_normalizes_aliases_and_cancellation_status() -> None:
    result = BookingCardData.from_mapping(
        {
            "status": "CONFIRMED",
            "first_name": "Alex",
            "last_name": "Morgan",
            "guests": 2,
            "arrival": "2030-06-10",
            "departure": "2030-06-13",
            "total_prize": {"amount": "300.00", "currency": "EUR"},
            "breakfast_included": True,
            "is_accessible": False,
        }
    )

    assert result is not None
    assert result.guest_name == "Alex Morgan"
    assert result.guest_count == 2
    assert result.total_price == {"amount": "300.00", "currency": "EUR"}
    assert result.is_cancellation_candidate is True
    assert BookingCardData.from_mapping({"email": "alex@example.com"}) is None


def test_booking_card_without_id_or_active_status_is_not_cancellable() -> None:
    result = BookingCardData.from_mapping({"room_category": "double"})

    assert result is not None
    assert result.is_cancellation_candidate is False
