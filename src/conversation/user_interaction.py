"""Handle user communication."""

from collections.abc import Mapping, Sequence
from datetime import date

from api.schemas.availability_schema import AvailabilityRequestResponse
from api.schemas.availability_schema import (
    AvailabilityResponse as ApiAvailabilityResponse,
)
from configuration.application import ApplicationSettings
from conversation.entities.interaction_response import (
    AskConfirmationResponse,
    AvailabilityResponse,
    BookingResponse,
    EmptyInteractionResponse,
    ErrorResponse,
    GreetingResponse,
    InformationResponse,
    InteractionResponse,
)
from conversation.entities.message import Message
from conversation.value_object.action import Action
from conversation.value_object.default_phrases import DefaultPhrases, build
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent
from domain.entities.booking_request import BookingRequest
from domain.entities.room import Room
from observability.log_messages import LOG_MSG
from observability.utils.to_json import to_jsonable


class UserInteraction:
    def __init__(self) -> None:
        self.settings = ApplicationSettings.get_settings()

    def parse_message(self, raw_message: str) -> Message | None:
        """Normalize user input and enforce message rules."""

        msg = raw_message.strip()

        if len(msg) > self.settings.msg_max_length:
            LOG_MSG.debug("Too long message detected")
            return None

        return Message(
            content=msg,
            original_content=msg,
        )

    def send_error_msg(
        self,
        reason: str,
        *,
        session_active: bool = True,
    ) -> ErrorResponse:
        """Build an error response without terminating the session by default."""

        return ErrorResponse(
            text=DefaultPhrases.ERROR_MESSAGE,
            session_active=session_active,
            reason=reason,
        )

    def send_empty_response(self) -> EmptyInteractionResponse:
        return EmptyInteractionResponse()

    def build_response(
        self,
        action: Action,
        intent: Intent,
        data: object,
    ) -> InteractionResponse:
        """Build the response belonging to the selected conversation action."""

        methods = {
            Action.ASK_FOR_DATA: self.ask_for_data,
            Action.ASK_FOR_CONFIRMATION: self.ask_for_confirmation,
            Action.ASK_FOR_INFORMATION_CHANGE: self.ask_for_information_change,
            Action.REPORT_INVALID_DATE: self.report_invalid_date,
            Action.REPORT_REUSED_DATE: self.report_reused_date,
            Action.REPORT_EMAIL_IN_USE: self.report_email_in_use,
            Action.DISPLAY_AVAILABILITY: self.display_availability,
            Action.DISPLAY_BOOKING: self.display_booking,
            Action.DISPLAY_GREETING: self.display_greeting,
            Action.DISPLAY_INFO: self.display_info,
            Action.ASK_INTENT: self.ask_intent,
            Action.CONFIRMATION_DECLINED: self.ask_further_intent
        }

        try:
            method = methods[action]
        except KeyError as error:
            raise ValueError(f"Unsupported interaction action: {action}") from error

        return method(intent=intent, data=data)

    def ask_for_data(
        self,
        intent: Intent,
        data: object,
    ) -> InteractionResponse:
        """Ask the user for information required by the active intent."""

        text = build(
            Action.ASK_FOR_DATA,
            intent=intent,
            missing_fields=data,
        )

        if intent == Intent.AVAILABILITY_CHECK:
            return AvailabilityResponse(
                session_active=True,
                text=text,
                content=data,
            )

        if intent in {
            Intent.BOOKING_CHECK,
            Intent.BOOKING_REQUEST,
            Intent.BOOKING_CANCELLATION,
        }:
            return BookingResponse(
                session_active=True,
                text=text,
                content=data,
            )

        if intent == Intent.INFORMATION_REQUEST:
            return InformationResponse(
                session_active=True,
                text=text,
            )

        return InteractionResponse(
            session_active=True,
            text=text,
        )

    def ask_for_confirmation(
        self,
        intent: Intent,
        data: object,
    ) -> AskConfirmationResponse:
        """Ask the user to confirm a pending operation."""

        text = build(
            Action.ASK_FOR_CONFIRMATION,
            intent=intent,
            missing_fields=[],
        )

        return AskConfirmationResponse(
            session_active=True,
            text=text,
            data=data,
        )

    def ask_for_information_change(
        self,
        intent: Intent,
        data: object,
    ) -> InteractionResponse:
        """Ask once for confirmation of one or more replacement values."""

        if not isinstance(data, Mapping) or not data:
            raise TypeError(
                "Information-change confirmation requires replacement values"
            )

        replacements: list[str] = []

        for field, values in data.items():
            try:
                normalized_field = (
                    field
                    if isinstance(field, InformationField)
                    else InformationField(field)
                )
            except (TypeError, ValueError):
                raise TypeError(
                    "Invalid information-change confirmation data"
                ) from None

            if (
                not isinstance(values, Sequence)
                or isinstance(values, (str, bytes))
                or len(values) != 2
            ):
                raise TypeError(
                    "Invalid information-change confirmation data"
                )

            old_value, new_value = values
            label = normalized_field.value.replace("_", " ")
            replacements.append(
                f"{label}: {_display_value(old_value)} to "
                f"{_display_value(new_value)}"
            )

        if len(replacements) == 1:
            text = (
                "Should the existing value be replaced? "
                f"{replacements[0]}."
            )
        else:
            text = (
                "Should these existing values be replaced? "
                f"{'; '.join(replacements)}."
            )

        return InteractionResponse(
            session_active=True,
            text=text,
        )

    def report_invalid_date(
        self,
        intent: Intent,
        data: object,
    ) -> InteractionResponse:
        """Tell the user that a requested date field cannot use the value."""

        if data == InformationField.CHECK_OUT:
            text = (
                "The specified date cannot be used as the check-out date. "
                "Please provide a check-out date after the check-in date "
                "and not in the past."
            )
        elif data == InformationField.CHECK_IN:
            text = (
                "The specified date cannot be used as the check-in date. "
                "Please provide a check-in date that is not in the past "
                "and before the check-out date."
            )
        else:
            raise TypeError("Invalid-date response requires a date field")

        return InteractionResponse(
            session_active=True,
            text=text,
        )

    def report_reused_date(
        self,
        intent: Intent,
        data: object,
    ) -> InteractionResponse:
        """Tell the user that the supplied date is already in use."""

        if data == InformationField.CHECK_IN:
            date_role = "check-in"
        elif data == InformationField.CHECK_OUT:
            date_role = "check-out"
        else:
            raise TypeError("Reused-date response requires a date field")

        return InteractionResponse(
            session_active=True,
            text=f"That date is already being used as your {date_role} date.",
        )

    def report_email_in_use(
        self,
        intent: Intent,
        data: object,
    ) -> ErrorResponse:
        """Explain that an email belongs to a different guest identity."""

        return ErrorResponse(
            session_active=True,
            text=DefaultPhrases.EMAIL_IN_USE,
            reason="Email address is already in use by another guest",
        )

    def display_info(
        self,
        intent: Intent,
        data: object,
    ) -> InformationResponse:
        """Display general hotel information."""

        if not isinstance(data, str):
            err = (
                "Expected string response from information request. "
                f"System responded with: {data!r}"
            )
            LOG_MSG.error(
                err,
                extra=to_jsonable({"data": data}),
            )
            raise TypeError(err)

        return InformationResponse(
            text=data,
            session_active=True,
        )

    def display_availability(
        self,
        intent: Intent,
        data: object,
    ) -> AvailabilityResponse:
        """Display available room categories."""

        if data is None or not hasattr(data, "rooms"):
            err = (
                "Expected availability domain data containing a 'rooms' attribute. "
                f"Received: {type(data).__name__}"
            )
            LOG_MSG.error(
                err,
                extra=to_jsonable({"data": data}),
            )
            raise TypeError(err)

        content = ApiAvailabilityResponse(
            request=_availability_request_response(getattr(data, "request", None))
        )

        rooms = data.rooms

        if not rooms:
            return AvailabilityResponse(
                text=DefaultPhrases.NO_VACANCY,
                session_active=True,
                content=content,
            )

        for room in rooms:
            if not isinstance(room, Room):
                err = (
                    "Expected Room objects in availability result. "
                    f"Received invalid object: {room!r}"
                )
                LOG_MSG.error(
                    err,
                    extra=to_jsonable({"data": data}),
                )
                raise TypeError(err)

            content.add_room(room=room)

        return AvailabilityResponse(
            session_active=True,
            text=DefaultPhrases.AVAILABLE_ROOM_CATEGORIES,
            content=content,
        )

    def display_booking(
        self,
        intent: Intent,
        data: object,
    ) -> BookingResponse:
        """Display an existing, created, cancelled, or previewed booking."""

        if data is None:
            return BookingResponse(
                text=DefaultPhrases.BOOKING_NOT_FOUND,
                session_active=True,
                content=None,
            )

        return BookingResponse(
            session_active=True,
            text=DefaultPhrases.DISPLAY_BOOKING,
            content=data,
        )

    def display_greeting(
        self,
        intent: Intent,
        data: object,
    ) -> GreetingResponse:
        """Display the initial conversation greeting."""

        if not isinstance(data, str) or not data.strip():
            raise TypeError("Greeting requires a valid session ID")

        return GreetingResponse(
            text=DefaultPhrases.GREETING,
            session_active=True,
            session_id=data,
        )

    def ask_intent(
        self,
        intent: Intent,
        data: object,
    ) -> InteractionResponse:
        """Ask the user what they would like to do."""

        return InteractionResponse(
            text=DefaultPhrases.ASK_INTENT,
            session_active=True,
        )

    def ask_further_intent(
            self,
            intent: Intent,
            data: object,
    ) -> InteractionResponse:
        """After a declined confirmation, ask for a new intent"""
        text = build(
            Action.CONFIRMATION_DECLINED,
            intent=intent,
            missing_fields=[]
        )
        return InteractionResponse(
            session_active=True,
            text=text
        )


def _display_value(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _availability_request_response(
    request: object,
) -> AvailabilityRequestResponse | None:
    if not isinstance(request, BookingRequest):
        return None

    return AvailabilityRequestResponse(
        check_in=request.stay_period.check_in,
        check_out=request.stay_period.check_out,
        guest_count=request.guest_count,
        accessible=request.accessible_requested,
    )
