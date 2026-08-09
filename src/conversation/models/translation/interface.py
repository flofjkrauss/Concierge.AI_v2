"""Generic interface for translator modules."""

from abc import ABC, abstractmethod

from conversation.entities.message import Message


class TranslatorInterface(ABC):
    """Define the data operations required by the business services."""

    @abstractmethod
    def translate(self, text: Message, target_lang: str) -> Message:
        """Translates text to target language"""

    @abstractmethod
    def determine(self, text: Message) -> str:
        """Tries to determine the language of text"""

class NoneTranslator(TranslatorInterface):
    """Dummy for translator modules. Always determines language as 'en' and gives the exact same text back"""
    def translate(self, text: Message, target_lang: str) -> Message:
        return Message(content=f"{text.content}", original_content=text.original_content)

    def determine(self, text: Message) -> str:
        return "de"