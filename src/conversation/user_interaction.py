"""handle user communication"""
from api.schemas.availability_schema import AvailabilityResponse as ApiAvailabilityResponse

from domain.entities.room import Room

from configuration.application import ApplicationSettings
from conversation.entities.interaction_response import (
    EmptyInteractionResponse,
    ErrorResponse,
    InteractionResponse,
    InformationResponse,
    GreetingResponse,
    AvailabilityResponse,
    BookingResponse,
    AskConfirmationResponse,
    UserOptions

)
from conversation.entities.message import Message
from conversation.value_object.action import Action
from conversation.value_object.default_phrases import DefaultPhrases, build
from conversation.value_object.intent import Intent
from observability.log_messages import LOG_MSG


class UserInteraction:
    def __init__(self) -> None:
        self.settings = ApplicationSettings.get_settings()

    def parse_message(self, raw_message: str) -> Message | None:
        """enforce message rules"""
        msg = raw_message.strip()
        if len(msg) > self.settings.msg_max_length:
            LOG_MSG.debug("Too long message detected")
            return None
        return Message(
            content=msg,
            original_content=msg
        )


    def send_error_msg(self, reason: str) -> ErrorResponse:
        response = ErrorResponse(
            text=DefaultPhrases.ERROR_MESSAGE,
            session_active=False,
            reason=reason
        )
        return response

    def send_empty_response(self) -> EmptyInteractionResponse:
        return EmptyInteractionResponse()

    def build_response(self, action: Action, intent: Intent, data: object) -> InteractionResponse:
        methods = {
            Action.ASK_FOR_DATA: self.ask_for_data,
            Action.ASK_FOR_CONFIRMATION: self.ask_for_confirmation,
            Action.DISPLAY_AVAILABILITY: self.display_availability,
            Action.DISPLAY_BOOKING: self.display_booking,
            Action.DISPLAY_GREETING: self.display_greeting,
            Action.DISPLAY_INFO: self.display_info,
            Action.ASK_INTENT: self.ask_intent
        }
        return methods[action](intent=intent, data=data)

    def ask_for_data(self, intent: Intent, data: object) -> InteractionResponse:
        text = build(Action.ASK_FOR_DATA, intent=intent, missing_fields=data)
        if intent == Intent.AVAILABILITY_CHECK:
            return AvailabilityResponse(session_active=True,
                                        text=text,
                                        content=data)
        else:
            return BookingResponse(session_active=True,
                                    text=text,
                                    content=data)

    def ask_for_confirmation(self, intent: Intent, data: object) -> InteractionResponse:
        options = [
            UserOptions.CONFIRMED,
            UserOptions.DECLINED,
            UserOptions.INTERRUPTED
        ]
        text = build(Action.ASK_FOR_CONFIRMATION, intent=intent, missing_fields=[])
        return AskConfirmationResponse(session_active=True,
                                text=text,
                                options=options)
    
    def display_info(self, intent: Intent, data: object) -> InteractionResponse:
        if not isinstance(data, str):
            err = f"Expected string as respond from information request. System resonded: {data}"
            LOG_MSG.error(err, extra=data)
            raise TypeError(err)
        return InformationResponse(text=data, session_active=True)
    
    def display_availability(self, intent: Intent, data: object) -> InteractionResponse:
        content = ApiAvailabilityResponse(
            request_id=""
        )
        for room in data:
            if not isinstance(room, Room):
                err = f"Expected list of room objects (domain data). Invalid object in list: {room}"
                LOG_MSG.error(err, extra=data)
                raise TypeError(err)
            content.add_room(room=room)

        return AvailabilityResponse(session_active=True, text=DefaultPhrases.AVAILABLE_ROOM_CATEGORIES, content=content)
    
    def display_booking(self, intent: Intent, data: object) -> InteractionResponse:
        if not data:
            return InteractionResponse(text=DefaultPhrases.BOOKING_NOT_FOUND, session_active=True)
        return BookingResponse(session_active=True,
                                text=DefaultPhrases.DISPLAY_BOOKING,
                                content=data)
    
    def display_greeting(self, intent: Intent, data: object) -> GreetingResponse:
        if not isinstance(data, str):
            err = f"Expected string as session_id. System resonded: {data}"
            LOG_MSG.error(err, extra=data)
            raise TypeError(err)
        return GreetingResponse(text=DefaultPhrases.GREETING, session_active=True, session_id=data)
    
    def ask_intent(self, intent: Intent, data: object) -> InteractionResponse:
        return InteractionResponse(text=DefaultPhrases.ASK_INTENT, session_active=True)
    

