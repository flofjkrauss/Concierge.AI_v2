"""Generic interface for translator modules."""

from abc import ABC, abstractmethod

from configuration.application import ApplicationSettings
from conversation.entities.message import Message


class TranslatorInterface(ABC):
    """Define the data operations required by the business services."""

    @abstractmethod
    def translate(self, text: Message, target_lang: str, source_lang: str) -> Message:
        """Translates text to target language"""

    @abstractmethod
    def determine(self, text: Message) -> str:
        """Tries to determine the language of text"""

class NoneTranslator(TranslatorInterface):
    """
    Dummy for translator modules. Always determines language as domain language. 
    As consequence LangGraph will skip the translation.
    If you want the translate method to be executed, set a fixed value as result of determine that differs from set domain language.
    """
    def translate(self, text: Message, target_lang: str, source_lang: str) -> Message:
        return Message(content=f"{text.content}", original_content=text.original_content)

    def determine(self, text: Message) -> str:
        return ApplicationSettings.get_settings().domain_language
