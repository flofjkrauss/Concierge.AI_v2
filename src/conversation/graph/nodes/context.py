"""Dependency contract shared by individual conversation node functions."""

from typing import Protocol

from conversation.models.information.interface import InformationExtractorInterface
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.models.translation.interface import TranslatorInterface
from conversation.user_interaction import UserInteraction

from .domain_adapter import ConversationDomainAdapter


class ConversationNodeContext(Protocol):
    """Dependencies and settings available to every graph node."""

    translator: TranslatorInterface
    intent_classifier: IntentionDetectorInterface
    information_extractor: InformationExtractorInterface
    user_interaction: UserInteraction
    domain_adapter: ConversationDomainAdapter
    domain_language: str
    max_unknown_messages: int


__all__ = ["ConversationNodeContext"]
