from conversation.conversation_controller import ConversationController
from conversation.information_extrator import InformationExtractor
from conversation.intent_classifier import IntentClassifier
from conversation.models.translation.interface import NoneTranslator
from conversation.session_manager import SessionManager
from conversation.user_interaction import UserInteraction
from database.interface import DatabaseInterface


def init(database: DatabaseInterface) -> ConversationController:
    if not isinstance(database, DatabaseInterface):
        raise TypeError(
            "Invalid database parameter for conversation controller init"
        )
    controller = ConversationController(
        database=database,
        session_mgr=SessionManager(),
        info_extractor=InformationExtractor(),
        intent_classifier=IntentClassifier(),
        user_interaction=UserInteraction(),
        translator=NoneTranslator()
    )

    return controller