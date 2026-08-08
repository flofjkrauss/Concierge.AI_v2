from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import get_database
from api.schemas.availability_schema import AvailabilityResponse, RoomResponse
from database.interface import DatabaseInterface
from domain.entities.booking_request import BookingRequest
from domain.services.find_matching_rooms import find_matching_rooms
from observability.log_messages import LOG_MSG

router = APIRouter(
    prefix="/api/availability",
    tags=["bookings"],
)


@router.post("/")
def read_availability(
    booking_request: BookingRequest,
    database: Annotated[
        DatabaseInterface,
        Depends(get_database),
    ],
) -> AvailabilityResponse:
    LOG_MSG.debug(f"Incoming request {booking_request}")
    rooms = find_matching_rooms(booking_request=booking_request, database=database)
    
    response = AvailabilityResponse(
        request_id=booking_request.request_id,
    )
    for room in rooms:
        response.add_room(room)

    return response
