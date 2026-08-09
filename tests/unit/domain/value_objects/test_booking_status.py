from domain.value_objects.booking_status import BookingStatus


def test_pending_and_confirmed_bookings_block_rooms() -> None:
    assert BookingStatus.PENDING.blocks_room
    assert BookingStatus.CONFIRMED.blocks_room


def test_cancelled_booking_does_not_block_room() -> None:
    assert not BookingStatus.CANCELLED.blocks_room
