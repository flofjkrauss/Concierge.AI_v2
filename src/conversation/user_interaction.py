"""Handle user communication."""

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
from conversation.value_object.intent import Intent
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
                extra=to_jsonable(data),
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
                extra=to_jsonable(data),
            )
            raise TypeError(err)

        content = ApiAvailabilityResponse()

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
                    extra=to_jsonable(data),
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
