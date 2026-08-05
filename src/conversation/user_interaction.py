"""handle user communication"""
from configuration.application import ApplicationSettings
from conversation.entities.interaction_response import (
    EmptyInteractionResponse,
    ErrorResponse,
    InteractionResponse,
)
from conversation.entities.message import Message
from conversation.value_object.action import Action
from conversation.value_object.default_phrases import DefaultPhrases
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
            content=msg
        )

    def send_session_id(self, session_id: str) -> InteractionResponse:
        response = InteractionResponse(
            session_active=True,
            text=session_id
        )
        return response

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
        return ErrorResponse(text="failed", session_active=False, reason="not yet implemented")

    def ask_for_confirmation(self, intent: Intent, data: object) -> InteractionResponse:
        return ErrorResponse(text="failed", session_active=False, reason="not yet implemented")
    
    def display_info(self, intent: Intent, data: object) -> InteractionResponse:
        return ErrorResponse(text="failed", session_active=False, reason="not yet implemented")
    
    def display_availability(self, intent: Intent, data: object) -> InteractionResponse:
        return ErrorResponse(text="failed", session_active=False, reason="not yet implemented")
    
    def display_booking(self, intent: Intent, data: object) -> InteractionResponse:
        return ErrorResponse(text="failed", session_active=False, reason="not yet implemented")
    
    def display_greeting(self, intent: Intent, data: object) -> InteractionResponse:
        return ErrorResponse(text="failed", session_active=False, reason="not yet implemented")
    
    def ask_intent(self, intent: Intent, data: object) -> InteractionResponse:
        return ErrorResponse(text="failed", session_active=False, reason="not yet implemented")
    

