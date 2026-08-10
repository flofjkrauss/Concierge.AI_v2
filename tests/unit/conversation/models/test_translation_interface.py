import pytest

from conversation.entities.message import Message
from conversation.models.translation.interface import (
    NoneTranslator,
    TranslatorInterface,
)


def test_translator_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        TranslatorInterface()


def test_none_translator_reports_english_language() -> None:
    translator = NoneTranslator()
    message = Message("Hello")

    assert translator.determine(message) == "en"


def test_none_translator_returns_original_message() -> None:
    translator = NoneTranslator()
    message = Message("Hello")

    assert translator.translate(message, "de") is message
