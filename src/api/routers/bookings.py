from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_database
from api.schemas.booking_schema import BookingResponse
from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from domain.services.cancel_booking import cancel_booking, cancel_booking_by_name
from domain.services.confirm_booking import confirm_booking
from domain.services.create_customer import create_customer, get_customer
from domain.services.get_booking import get_booking, get_booking_by_name
from domain.services.get_information import get_hotel_address, get_hotel_name
from domain.value_objects.room_category import RoomCategory
from observability.log_messages import LOG_MSG

router = APIRouter(
    prefix="/api/bookings",
    tags=["bookings"],
)

#delete this after development
from domain.services.find_matching_rooms import find_matching_rooms
from utils.connect_database import connect

DEBUG_MODE = False
DEBUG_CATEGORY = RoomCategory.FAMILY
class DebugData:
    FIRST_NAME: str = "test"
    LAST_NAME: str = "user"
    EMAIL: str = "mail@mail.com"
    PREFERRED_LANGUAGE: str = "de"


debug_booking_request = find_matching_rooms(
    check_in=date(2028, 10, 10),
    check_out=date(2028, 10, 20),
    guest_count=2,
    breakfast=True,
    accessible=False,
    database=connect()
)



@router.get("/booking_by_name")
def read_booking_by_name(
    database: Annotated[
        DatabaseInterface,
        Depends(get_database),
        ],
    last_name: str,
    email: str,
    check_in: str,
    ) -> BookingResponse | None:
    if DEBUG_MODE:
        last_name = DebugData.LAST_NAME
        email = DebugData.EMAIL
        check_in = str(debug_booking_request.request.stay_period.check_in)

    LOG_MSG.debug(f"Booking object requested for booking: {last_name} {email}")
    try:
        normalized_check_in = date.fromisoformat(check_in)
    except ValueError:
        LOG_MSG.error("Invalid data format received in read_booking_by_name check")
        return None
    
    booking = get_booking_by_name(
        last_name=last_name,
        email=email,
        check_in=normalized_check_in,
        database=database,
    )

    return _response_from_booking(booking=booking, database=database)

@router.post("/cancel_by_name")
def read_booking_to_cancel_by_name(
     database: Annotated[
        DatabaseInterface,
        Depends(get_database),
    ],
    last_name: str,
    email: str,
    check_in: str,
   
) -> BookingResponse | None:
    if DEBUG_MODE:
        last_name = DebugData.LAST_NAME
        email = DebugData.EMAIL
        check_in = str(debug_booking_request.request.stay_period.check_in)
    LOG_MSG.debug(f"Booking cancellation requested for booking by name: {last_name}")
    check_in_iso = date.fromisoformat(check_in)   

    booking = cancel_booking_by_name(
        last_name=last_name,
        email=email,
        check_in=check_in_iso,
        database=database,
    )

    return _response_from_booking(booking=booking, database=database)

@router.post("/request", response_model=BookingResponse)
def read_booking_request(
    database: Annotated[
            DatabaseInterface,
            Depends(get_database),
        ],
    booking_request: BookingRequest,
    room_category: str,
    first_name: str,
    last_name: str,
    email: str,
    preferred_language: str,
    
) -> BookingResponse | None:
    if DEBUG_MODE:
        booking_request = debug_booking_request.request
        room_category = DEBUG_CATEGORY
        first_name = DebugData.FIRST_NAME
        last_name = DebugData.LAST_NAME
        email = DebugData.EMAIL
        preferred_language = DebugData.PREFERRED_LANGUAGE
    try:
        LOG_MSG.debug(f"BookingRequest confirmation requested for request: {booking_request.request_id} and room category: {room_category}")
        try:
            RoomCategory(room_category)
        except ValueError:
            LOG_MSG.debug(f"Room category could not be found: {room_category}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room category not found: {room_category}"
            )
            
        customer = create_customer(database=database,
                                first_name=first_name,
                                last_name=last_name,
                                email=email,
                                preferred_language=preferred_language)

        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer not found and not created: {first_name} {last_name} {email}"
            )
        
        booking = confirm_booking(
            booking_request=booking_request,
            room_category=room_category,
            customer=customer,
            database=database
        )

        return _response_from_booking(booking=booking, database=database)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error)
        ) from error

@router.get("/{booking_id}")
def read_booking(
    database: Annotated[
        DatabaseInterface,
        Depends(get_database),
    ],
    booking_id: str,
    
) -> BookingResponse | None:
    if DEBUG_MODE:
        booking_id = debug_booking_request.request.request_id

    LOG_MSG.debug(f"Booking object requested for booking: {booking_id}")
    booking = get_booking(
        booking_id=booking_id,
        database=database,
    )
    return _response_from_booking(booking=booking, database=database)



@router.post("/{booking_id}/cancel")
def read_booking_to_cancel(
    database: Annotated[
        DatabaseInterface,
        Depends(get_database),
    ],
    booking_id: str,
    
) -> BookingResponse | None:
    if DEBUG_MODE:
        booking_id = debug_booking_request.request.request_id
    
    LOG_MSG.debug(f"Booking cancellation requested for booking: {booking_id}")
    booking = cancel_booking(
        booking_id=booking_id,
        database=database,
    )
    return _response_from_booking(booking=booking, database=database)


def _response_from_booking(
    booking: Booking | None,
    database: DatabaseInterface,
    ) -> BookingResponse | None :
    try:
        if not isinstance(booking, Booking):
            raise KeyError("booking is None")
        
        customer = get_customer(booking.customer_id, database=database)
        if customer is None:
            raise KeyError("customer is None")
        
        hotel_name = get_hotel_name(database=database)
        hotel_address = get_hotel_address(database=database)
        room = database.get_room(booking.room_id)
        if not isinstance(room, Room):
            return None
        category = room.category

        return BookingResponse(
            booking_id=booking.booking_id,
            room_category=category,
            guest_name=customer.full_name,
            arrival=booking.stay_period.check_in,
            departure=booking.stay_period.check_out,
            guests=booking.guest_count,
            breakfast=booking.breakfast_included,
            total_price=booking.total_price,
            hotel_name=hotel_name,
            hotel_address=hotel_address,
            status=booking.status
        )
    except KeyError as error:
        LOG_MSG.debug("no booking objekt for response creation.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error)
        ) from error