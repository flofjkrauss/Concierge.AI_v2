"""Focused branch tests for input language normalization."""

from datetime import date
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

from conversation.entities.message import Message
from conversation.graph.nodes.context import ConversationNodeContext
from conversation.graph.nodes.translate_input import translate_input
from conversation.graph.state import ConversationState
from conversation.models.translation.interface import TranslatorInterface
from conversation.value_object.booking_selection import BookingSelection
from conversation.value_object.information_fields import InformationField
from conversation.value_object.information_topic_selection import (
    InformationTopicSelection,
)
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.room_category import RoomCategory


def _context(translator: Mock) -> ConversationNodeContext:
    return cast(
        ConversationNodeContext,
        SimpleNamespace(translator=translator, domain_language="en"),
    )


def _state(**values: object) -> ConversationState:
    return cast(ConversationState, values)


def test_booking_selection_uses_session_language_without_translation() -> None:
    translator = Mock(spec=TranslatorInterface)
    wire = BookingSelection(
        date(2030, 6, 10),
        date(2030, 6, 13),
        2,
        False,
        RoomCategory.DOUBLE,
    ).to_wire()

    result = translate_input(
        _context(translator),
        _state(parsed_message=Message(wire), language="de"),
    )

    assert result["translated_message"].content == wire  # type: ignore[union-attr]
    assert result["collected_information"][InformationField.PREFERRED_LANG].content == "de"  # type: ignore[index]
    translator.determine.assert_not_called()
    translator.translate.assert_not_called()


def test_information_topic_selection_is_not_translated() -> None:
    translator = Mock(spec=TranslatorInterface)
    wire = InformationTopicSelection(InformationTopic.WIFI).to_wire()

    result = translate_input(
        _context(translator),
        _state(parsed_message=Message(wire), language="de"),
    )

    assert result["translated_message"].content == wire  # type: ignore[union-attr]
    assert result["language"] == "de"
    translator.determine.assert_not_called()
    translator.translate.assert_not_called()


def test_detection_exception_uses_domain_language() -> None:
    translator = Mock(spec=TranslatorInterface)
    translator.determine.side_effect = RuntimeError("detector failed")

    result = translate_input(
        _context(translator),
        _state(parsed_message=Message("Hello"), language=None),
    )

    assert result["language"] == "en"
    translator.translate.assert_not_called()


def test_invalid_translation_falls_back_to_original_message() -> None:
    translator = Mock(spec=TranslatorInterface)
    translator.determine.return_value = "de"
    translator.translate.return_value = object()
    parsed = Message("Hallo")

    result = translate_input(
        _context(translator),
        _state(parsed_message=parsed, language=None),
    )

    normalized = result["translated_message"]
    assert normalized.content == "Hallo"  # type: ignore[union-attr]
    assert normalized.original_content == "Hallo"  # type: ignore[union-attr]
    assert normalized.language == "de"  # type: ignore[union-attr]
