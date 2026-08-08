from typing import Annotated
from datetime import date

from fastapi import APIRouter, Depends

from api.dependencies import get_database
from api.schemas.availability_schema import AvailabilityResponse
from database.interface import DatabaseInterface
from domain.services.find_matching_rooms import find_matching_rooms, MatchResponse
from observability.log_messages import LOG_MSG
from api.routers.bookings import DEBUG_MODE, debug_booking_request

router = APIRouter(
    prefix="/api/availability",
    tags=["bookings"],
)


@router.post("/")
def read_availability(
    database: Annotated[
            DatabaseInterface,
            Depends(get_database),
        ],
    check_in: str | None=None,
    check_out: str | None=None,
    guest_count: int | None=None,
    breakfast: bool | None=None,
    accessible: bool | None=None,
    
) -> AvailabilityResponse:

    if DEBUG_MODE:
        check_in = str(debug_booking_request.request.stay_period.check_in)
        check_out = str(debug_booking_request.request.stay_period.check_out)
        guest_count = debug_booking_request.request.guest_count
        breakfast = debug_booking_request.request.breakfast_included
        accessible = debug_booking_request.request.accessible_requested
    try:
        normalized_check_in = date.fromisoformat(check_in)
        normalized_check_out = date.fromisoformat(check_out)
        normalized_guest_count = int(guest_count)
        normalized_breakfast = bool(breakfast)
        normalized_accesible = bool(accessible)
    except ValueError:
        LOG_MSG.error(f"Invalid data format received in availability check")
        return AvailabilityResponse()
    
    match_response = find_matching_rooms(
    check_in=normalized_check_in,
    check_out=normalized_check_out,
    guest_count=normalized_guest_count,
    breakfast=normalized_breakfast,
    accessible=normalized_accesible,
    database=database
    )

    response = AvailabilityResponse()

    for room in match_response.rooms:
        response.add_room(room)

    return response
