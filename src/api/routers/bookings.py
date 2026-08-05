from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_database
from api.schemas.booking_schema import BookingResponse
from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.services.cancel_booking import cancel_booking
from domain.services.confirm_booking import confirm_booking, get_room
from domain.services.create_customer import create_customer, get_customer
from domain.services.get_booking import get_booking
from domain.services.get_information import get_hotel_address, get_hotel_name
from observability.log_messages import LOG_MSG

router = APIRouter(
    prefix="/api/bookings",
    tags=["bookings"],
)


@router.get("/{booking_id}")
def read_booking(
    booking_id: str,
    database: Annotated[
        DatabaseInterface,
        Depends(get_database),
    ],
) -> BookingResponse | None:
    LOG_MSG.debug(f"Booking object requested for booking: {booking_id}")
    booking = get_booking(
        booking_id=booking_id,
        database=database,
    )
    return _response_from_booking(booking=booking, database=database)

@router.post("/{booking_id}/cancel")
def read_booking_to_cancel(
    booking_id: str,
    database: Annotated[
        DatabaseInterface,
        Depends(get_database),
    ],
) -> BookingResponse | None:
    LOG_MSG.debug(f"Booking cancellation requested for booking: {booking_id}")
    booking = cancel_booking(
        booking_id=booking_id,
        database=database,
    )
    return _response_from_booking(booking=booking, database=database)

@router.post("/request", response_model=BookingResponse)
def read_booking_request(
    booking_request: BookingRequest,
    room_id: str,
    first_name: str,
    last_name: str,
    email: str,
    preferred_language: str,
    database: Annotated[
        DatabaseInterface,
        Depends(get_database),
    ],
) -> BookingResponse | None:
    try:
        LOG_MSG.debug(f"BookingRequest confirmation requested for request: {booking_request.request_id} and room: {room_id}")
        room = get_room(room_id=room_id, database=database)
        if room is None:
            LOG_MSG.debug(f"Room could not be found: {room_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room not found: {room_id}"
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
            room=room,
            customer=customer,
            database=database
        )

        return _response_from_booking(booking=booking, database=database)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error)
        ) from error

def _response_from_booking(
    booking: Booking | None,
    database: DatabaseInterface,
    ) -> BookingResponse | None :
    try:
        if booking is None:
            raise KeyError("booking is None")
        
        customer = get_customer(booking.customer_id, database=database)
        if customer is None:
            raise KeyError("customer is None")
        
        hotel_name = get_hotel_name(database=database)
        hotel_address = get_hotel_address(database=database)

        return BookingResponse(
            booking_id=booking.booking_id,
            customer_id=booking.customer_id,
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