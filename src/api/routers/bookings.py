from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import get_database
from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.services.get_booking import get_booking

router = APIRouter(
    prefix="/api/v1/bookings",
    tags=["bookings"],
)


@router.get("/{booking_id}")
def read_booking(
    booking_id: str,
    database: Annotated[
        DatabaseInterface,
        Depends(get_database),
    ],
) -> Booking | None:
    return get_booking(
        booking_id=booking_id,
        database=database,
    )