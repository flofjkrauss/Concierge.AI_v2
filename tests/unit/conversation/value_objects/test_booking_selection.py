"""Tests for the trusted room-selection wire value."""

from datetime import date

import pytest

from conversation.value_object.booking_selection import BookingSelection
from domain.value_objects.room_category import RoomCategory


def test_booking_selection_round_trips_exact_wire_contract() -> None:
    selection = BookingSelection(
        check_in=date(2030, 6, 10),
        check_out=date(2030, 6, 13),
        guest_count=2,
        accessible=True,
        room_category=RoomCategory.DOUBLE,
    )

    assert BookingSelection.from_wire(selection.to_wire()) == selection


@pytest.mark.parametrize(
    "message",
    [
        "normal guest text",
        "__concierge_booking_selection_v1__|2030-06-10",
        "__concierge_booking_selection_v1__|2030-06-10|2030-06-13|2|yes|double",
        "__concierge_booking_selection_v1__|invalid|2030-06-13|2|true|double",
        "__concierge_booking_selection_v1__|2030-06-10|2030-06-13|0|true|double",
        "__concierge_booking_selection_v1__|2030-06-10|2030-06-13|2|true|suite",
    ],
)
def test_booking_selection_rejects_non_contract_or_invalid_wire(message: str) -> None:
    assert BookingSelection.from_wire(message) is None


def test_booking_selection_validates_stay_and_guest_count() -> None:
    with pytest.raises(ValueError):
        BookingSelection(
            check_in=date(2030, 6, 13),
            check_out=date(2030, 6, 10),
            guest_count=2,
            accessible=False,
            room_category=RoomCategory.SINGLE,
        )
    with pytest.raises(ValueError, match="guest_count"):
        BookingSelection(
            check_in=date(2030, 6, 10),
            check_out=date(2030, 6, 13),
            guest_count=0,
            accessible=False,
            room_category=RoomCategory.SINGLE,
        )
