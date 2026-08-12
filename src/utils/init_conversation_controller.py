"""Create the application-scoped conversation controller."""

from conversation.conversation_controller import ConversationController
from conversation.graph.builder import (
    build_conversation_graph,
    create_in_memory_checkpointer,
)
from conversation.models.information.information_extrator import InformationExtractor
from conversation.models.intent.intent_classifier import IntentClassifier
from conversation.models.translation.m2m100_translator import M2M100Translator
from conversation.user_interaction import UserInteraction
from database.interface import DatabaseInterface


def init(database: DatabaseInterface) -> ConversationController:
    """Build shared dependencies and one in-memory conversation graph."""

    if not isinstance(database, DatabaseInterface):
        raise TypeError("Invalid database parameter for conversation controller init")

    print("Loading models...")
    translator = M2M100Translator()
    intent_classifier = IntentClassifier()
    information_extractor = InformationExtractor()
    user_interaction = UserInteraction()
    checkpointer = create_in_memory_checkpointer()

    
    graph = build_conversation_graph(
        database=database,
        translator=translator,
        intent_classifier=intent_classifier,
        information_extractor=information_extractor,
        user_interaction=user_interaction,
        checkpointer=checkpointer
    )
    return ConversationController(
        graph=graph,
        user_interaction=user_interaction,
    )
