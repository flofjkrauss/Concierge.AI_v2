"""Adapter boundary between graph operations and hotel domain services."""

from __future__ import annotations

from dataclasses import dataclass

from .support import (
    BookingResponseObject,
    BookingStatus,
    DatabaseInterface,
    DomainOperation,
    Information,
    InformationField,
    InformationTopic,
    Mapping,
    Protocol,
    _booking_request_tuple_from_information,
    _build_booking_response_data,
    _create_customer_from_information,
    _early_availability_tuple_from_information,
    _optional_string,
    _required_date,
    _required_string,
    assert_never,
    calculate_price,
    cancel_booking_by_name,
    confirm_booking,
    find_matching_rooms,
    get_booking_by_name,
    get_information,
)


class ConversationDomainAdapter(Protocol):
    """Translate conversation data into calls to existing domain services."""

    def execute(
        self,
        operation: DomainOperation,
        information: Mapping[InformationField, Information],
    ) -> object:
        """Execute one previously selected domain operation."""


@dataclass(frozen=True, slots=True)
class DatabaseDomainAdapter:
    """Minimal adapter from collected fields to current domain-service calls."""

    database: DatabaseInterface

    def execute(
        self,
        operation: DomainOperation,
        information: Mapping[InformationField, Information],
    ) -> object:
        """Execute ``operation`` without moving business rules into LangGraph."""

        match operation:
            case (
                DomainOperation.FIND_AVAILABILITY
                | DomainOperation.CHECK_BOOKING_AVAILABILITY
            ):
                if operation == DomainOperation.CHECK_BOOKING_AVAILABILITY:
                    (
                        check_in,
                        check_out,
                        guest_count,
                        accessible,
                        breakfast,
                    ) = _early_availability_tuple_from_information(information)
                else:
                    (
                        check_in,
                        check_out,
                        guest_count,
                        accessible,
                        breakfast,
                    ) = _booking_request_tuple_from_information(information)

                room_category = _optional_string(
                    information,
                    InformationField.ROOM_CATEGORY,
                    default="",
                )

                return find_matching_rooms(
                    check_in=check_in,
                    check_out=check_out,
                    guest_count=guest_count,
                    breakfast=breakfast,
                    accessible=accessible,
                    database=self.database,
                    room_category=room_category,
                )

            case DomainOperation.GET_BOOKING:
                last_name = _required_string(
                    information,
                    InformationField.LAST_NAME,
                )
                email = _required_string(
                    information,
                    InformationField.EMAIL,
                )
                check_in = _required_date(
                    information,
                    InformationField.CHECK_IN,
                )

                booking = get_booking_by_name(
                    last_name=last_name,
                    email=email,
                    check_in=check_in,
                    database=self.database,
                )

                return _build_booking_response_data(
                    booking=booking,
                    database=self.database,
                )

            case DomainOperation.CREATE_BOOKING:
                room_category = _required_string(
                    information,
                    InformationField.ROOM_CATEGORY,
                )

                (
                    check_in,
                    check_out,
                    guest_count,
                    accessible,
                    breakfast,
                ) = _booking_request_tuple_from_information(information)

                match_response = find_matching_rooms(
                    check_in=check_in,
                    check_out=check_out,
                    guest_count=guest_count,
                    breakfast=breakfast,
                    accessible=accessible,
                    database=self.database,
                    room_category=room_category,
                )

                if not match_response.rooms:
                    return match_response

                if match_response.request is None:
                    raise RuntimeError(
                        "Availability result contains rooms without a request"
                    )

                customer = _create_customer_from_information(
                    information,
                    database=self.database,
                )

                booking = confirm_booking(
                    booking_request=match_response.request,
                    room_category=room_category,
                    customer=customer,
                    database=self.database,
                )

                return _build_booking_response_data(
                    booking=booking,
                    database=self.database,
                )

            case DomainOperation.CANCEL_BOOKING:
                last_name = _required_string(
                    information,
                    InformationField.LAST_NAME,
                )
                email = _required_string(
                    information,
                    InformationField.EMAIL,
                )
                check_in = _required_date(
                    information,
                    InformationField.CHECK_IN,
                )

                booking = cancel_booking_by_name(
                    last_name=last_name,
                    email=email,
                    check_in=check_in,
                    database=self.database,
                )

                return _build_booking_response_data(
                    booking=booking,
                    database=self.database,
                )

            case DomainOperation.PREVIEW_BOOKING:
                room_category = _required_string(
                    information,
                    InformationField.ROOM_CATEGORY,
                )
                first_name = _required_string(
                    information,
                    InformationField.FIRST_NAME,
                )
                last_name = _required_string(
                    information,
                    InformationField.LAST_NAME,
                )
                phone = _optional_string(
                    information,
                    InformationField.PHONE,
                    default="not given",
                )
                email = _required_string(
                    information,
                    InformationField.EMAIL,
                )

                (
                    check_in,
                    check_out,
                    guest_count,
                    accessible,
                    breakfast,
                ) = _booking_request_tuple_from_information(information)

                match_response = find_matching_rooms(
                    check_in=check_in,
                    check_out=check_out,
                    guest_count=guest_count,
                    breakfast=breakfast,
                    accessible=accessible,
                    database=self.database,
                    room_category=room_category,
                )

                if not match_response.rooms:
                    return match_response

                if match_response.request is None:
                    raise RuntimeError(
                        "Availability result contains rooms without a request"
                    )

                room = match_response.rooms[0]

                total_price = calculate_price(
                    booking_request=match_response.request,
                    room=room,
                    database=self.database,
                )

                return BookingResponseObject(
                    status=BookingStatus.PENDING,
                    room_category=room_category,
                    guest_count=guest_count,
                    check_in=check_in,
                    check_out=check_out,
                    total_prize=total_price,
                    accessible=accessible,
                    breakfast=breakfast,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                )

            case DomainOperation.GET_INFORMATION:
                topic_value = _required_string(
                    information,
                    InformationField.INFORMATION_TOPIC,
                )

                return get_information(
                    topic=InformationTopic(topic_value),
                    database=self.database,
                )

            case _ as unreachable:
                assert_never(unreachable)


__all__ = ["ConversationDomainAdapter", "DatabaseDomainAdapter"]
