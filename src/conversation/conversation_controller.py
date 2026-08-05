"""conversation controller class"""

from configuration.application import ApplicationSettings
from conversation.entities.information import Information
from conversation.entities.interaction_response import InteractionResponse
from conversation.entities.message import Message
from conversation.entities.session import Session
from conversation.information_extrator import InformationExtractor
from conversation.intent_classifier import IntentClassifier
from conversation.models.translation.interface import TranslatorInterface
from conversation.session_manager import SessionManager
from conversation.user_interaction import UserInteraction
from conversation.value_object.action import Action
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent
from conversation.value_object.intent_information_mapping import IntentInformationMapper
from database.interface import DatabaseInterface
from observability.log_messages import LOG_MSG


class ConversationController:
    def __init__(
            self,
            database: DatabaseInterface,
            session_mgr: SessionManager,
            info_extractor: InformationExtractor,
            intent_classifier: IntentClassifier,
            user_interaction: UserInteraction,
            translator: TranslatorInterface
            ):
            self.database=database
            self.session_mgr=session_mgr
            self.info_extractor=info_extractor
            self.intent_classifier=intent_classifier
            self.user_interaction=user_interaction
            self.translator=translator
            self.language = ApplicationSettings.get_settings().domain_language

    def init_conversation(self) -> InteractionResponse:
        session = self.session_mgr.start_session()
        return self.user_interaction.send_session_id(session_id=session.session_id)

    def process_message(self, session_id: str, message: str) -> InteractionResponse:
        if not message.strip():
            return self.user_interaction.send_empty_response()
        session = self.session_mgr.get_session(session_id=session_id)
        if not session:
             return self.user_interaction.send_error_msg(reason="Session not found")
        msg_obj = self.user_interaction.parse_message(raw_message=message)
        if msg_obj is None:
            return self.user_interaction.send_error_msg(reason="Invalid message")

        if not session.language:
             target_language = self.translator.determine(msg_obj)
             if not target_language:
                  LOG_MSG.debug("Language could not be determined.")
             if target_language != self.language:
                session.language = target_language
                msg_obj = self.translator.translate(msg_obj, self.language)

        session.add_message(message=msg_obj)
        intent = self.intent_classifier.determine(message=msg_obj)
        informations = self.info_extractor.extract(message=msg_obj)
        if self.session_mgr.unknown_intent_threshold_exeeded(session=session, intent=intent, informations=informations):
            self.session_mgr.terminate_session(session=session)
            return self.user_interaction.send_error_msg(reason="No intent found")
        
        
        session.collector.store_informations(informations=informations)
        (action, action_intent) = self.determine_next_action(session=session, intent=intent)
        action_data = self.retrieve_domain_data(action=action, intent=action_intent, session=session)
        response = self.user_interaction.build_response(action=action,
                                                        intent=action_intent,
                                                        data=action_data,
                                                        )
        response.text = self.translator.translate(
             Message(content=response.text),
             target_lang=session.language
                  ).content
        return response

    def retrieve_domain_data(self, action: Action, intent: Intent, session: Session) -> str:
        return ""

    def determine_next_action(self, session: Session, intent: Intent) -> tuple[Action, Intent]:
        """figure out what to do next"""
        # first process intents which can be handled without data or confirmation
        match intent:
            case Intent.INFORMATION_REQUEST:
                return (Action.DISPLAY_INFO, intent)
            case Intent.CONVERSATION_INITIATION:
                return (Action.DISPLAY_GREETING, intent)
        # try to react to a knew intent first, if it requires data
        required_fields = IntentInformationMapper.determine_fields(intent=intent)
        # if there is a new data intent, set it (early intent switch)
        if len(required_fields) > 0:
            session.reset(intent=intent)
            session.missing_fields = self.determine_missing_fields(
                required_fields=required_fields,
                data=session.collector.provide_data()
            )
            return (Action.ASK_FOR_DATA, intent)
        else:
            # the new intent is not a data intent
            # try to fullfill the last data intent
            required_fields = IntentInformationMapper.determine_fields(intent=session.current_intent)
        # update session.missing_fields
        session.missing_fields = self.determine_missing_fields(
            required_fields=required_fields,
            data=session.collector.provide_data()
        )
        if len(session.missing_fields) > 0:
            # still fields missing, ask for data
            return (Action.ASK_FOR_DATA, session.current_intent)

        # session.missing_fields can only be empty at this point
        # check if last intent is fullfilled
        if not session.last_intent_fullfilled:
            # no data missing, but intent is not fullfilled, so it will be now
            session.last_intent_fullfilled = True
            match session.current_intent:
                case Intent.BOOKING_CHECK:
                    return (Action.DISPLAY_BOOKING, session.current_intent)
                case Intent.AVAILABILITY_CHECK:
                    return (Action.DISPLAY_AVAILABILITY, session.current_intent)
                case Intent.BOOKING_REQUEST:
                    return (Action.ASK_FOR_CONFIRMATION, session.current_intent)
                case Intent.BOOKING_CANCELLATION:
                    return (Action.ASK_FOR_CONFIRMATION, session.current_intent)

        # last intent fullfilled, no missing data, 
        # if the new intent is unknown, ask for intent
        if intent == Intent.UNKNOWN:
            return (Action.ASK_INTENT, intent)

        # on this point you have an intent switch (late intent switch)
        # reset intent fields
        session.reset(intent=intent)
        # this point means that the user completed a request and wants to perform another
        # or
        # the user declined a confirmation request
        return (Action.ASK_INTENT, intent)

    def determine_missing_fields(self,
              required_fields: list[InformationField],
              data: dict[InformationField, Information]
              ) -> list[InformationField]:
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
                continue
            if data[field].is_valid():
                continue
            else:
                missing_fields.append(field)
    
        return missing_fields