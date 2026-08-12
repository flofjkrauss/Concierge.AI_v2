"""Factory for application-configured conversation graph nodes."""

from configuration.application import ApplicationSettings
from conversation.models.information.interface import InformationExtractorInterface
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.models.translation.interface import TranslatorInterface
from conversation.user_interaction import UserInteraction

from .conversation_nodes import ConversationNodes
from .domain_adapter import ConversationDomainAdapter


def nodes_from_settings(
    *,
    translator: TranslatorInterface,
    intent_classifier: IntentionDetectorInterface,
    information_extractor: InformationExtractorInterface,
    user_interaction: UserInteraction,
    domain_adapter: ConversationDomainAdapter,
) -> ConversationNodes:
    """Create graph nodes from the existing application settings."""

    settings = ApplicationSettings.get_settings()

    return ConversationNodes(
        translator=translator,
        intent_classifier=intent_classifier,
        information_extractor=information_extractor,
        user_interaction=user_interaction,
        domain_adapter=domain_adapter,
        domain_language=settings.domain_language,
        max_unknown_messages=settings.max_num_msg_with_intent_unknown,
    )


__all__ = ["nodes_from_settings"]
