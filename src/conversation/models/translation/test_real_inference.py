"""Focused real-inference checks for the local translator."""

from datetime import UTC, datetime

import pytest

from conversation.entities.message import Message
from conversation.models.translation.m2m100_translator import (
    M2M100Translator,
    UnsupportedLanguageError,
)


@pytest.fixture(scope="module")
def translator() -> M2M100Translator:
    return M2M100Translator()


@pytest.mark.parametrize(
    ("content", "expected_language"),
    [
        ("Ich möchte ein Doppelzimmer buchen.", "de"),
        ("I would like to book a double room.", "en"),
        ("Oui, je voudrais réserver une chambre double.", "fr"),
    ],
)
def test_determine_real_languages(
    translator: M2M100Translator,
    content: str,
    expected_language: str,
) -> None:
    assert translator.determine(Message(content)) == expected_language


def test_translate_german_hotel_request_to_english(
    translator: M2M100Translator,
) -> None:
    created_at = datetime(2030, 1, 1, tzinfo=UTC)
    source = Message(
        "Ich möchte vom 12. September bis 15. September "
        "ein Doppelzimmer buchen.",
        original_content="original hotel request",
        language="de",
        message_id="hotel-request",
        created_at=created_at,
    )

    translated = translator.translate(source, "en")

    assert translated is not source
    assert source.content.startswith("Ich möchte")
    assert "double room" in translated.content.lower()
    assert "12" in translated.content
    assert "15" in translated.content
    assert translated.original_content == source.original_content
    assert translated.language == source.language
    assert translated.message_id == source.message_id
    assert translated.created_at is created_at


def test_translate_english_identity_to_german(
    translator: M2M100Translator,
) -> None:
    source = Message(
        "My name is John Smith and my email is john@example.com.",
        original_content="identity message",
        language="en",
    )

    translated = translator.translate(source, "de")

    assert "John Smith" in translated.content
    assert "john@example.com" in translated.content
    assert translated.content != source.content
    assert translated.original_content == source.original_content


def test_translate_french_hotel_request_to_english(
    translator: M2M100Translator,
) -> None:
    source = Message("Oui, je voudrais réserver une chambre double.")

    translated = translator.translate(source, "en")

    assert "double room" in translated.content.lower()


def test_repeated_calls_reuse_loaded_models(
    translator: M2M100Translator,
) -> None:
    model_id = id(translator._model)
    tokenizer_id = id(translator._tokenizer)
    detector_id = id(translator._language_detector)

    translator.determine(Message("This is another English message."))
    translator.translate(Message("Guten Morgen."), "en")

    assert id(translator._model) == model_id
    assert id(translator._tokenizer) == tokenizer_id
    assert id(translator._language_detector) == detector_id


def test_reject_unsupported_target_language(
    translator: M2M100Translator,
) -> None:
    with pytest.raises(UnsupportedLanguageError, match="not supported"):
        translator.translate(Message("Hello"), "xx")
