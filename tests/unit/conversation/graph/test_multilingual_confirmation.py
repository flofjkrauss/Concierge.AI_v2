"""Regression tests for model-based multilingual confirmation handling."""

from __future__ import annotations

from threading import Lock
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.graph.nodes.context import ConversationNodeContext
from conversation.graph.nodes.extract_information import extract_information
from conversation.graph.nodes.resolve_confirmation import resolve_confirmation
from conversation.graph.nodes.update_progress import update_progress
from conversation.graph.state import (
    ConfirmationOutcome,
    ConversationState,
    DomainOperation,
    ExpectedInteraction,
    ExpectedInteractionKind,
)
from conversation.models.information.information_extraction_system_prompt import (
    get_system_prompt,
)
from conversation.models.information.information_extrator import InformationExtractor
from conversation.models.information.interface import InformationExtractorInterface
from conversation.value_object.action import Action
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


def _state(**values: object) -> ConversationState:
    return cast(ConversationState, values)


def _context(extractor: Mock | None = None) -> ConversationNodeContext:
    return cast(
        ConversationNodeContext,
        SimpleNamespace(
            information_extractor=(
                extractor or Mock(spec=InformationExtractorInterface)
            ),
            max_unknown_messages=2,
        ),
    )


def _expected(
    kind: ExpectedInteractionKind = ExpectedInteractionKind.BOOKING_CONFIRMATION,
) -> ExpectedInteraction:
    return ExpectedInteraction(
        kind=kind,
        intent=Intent.BOOKING_REQUEST,
        operation=DomainOperation.CREATE_BOOKING,
    )


def _confirmation(value: str) -> Information:
    return Information(InformationField.CONFIRMATION, value)


def test_pending_confirmation_is_extracted_from_original_message() -> None:
    extractor = Mock(spec=InformationExtractorInterface)
    original = Message("ja")
    translated = Message("I", original_content=original.content)
    confirmation = _confirmation("yes")
    extractor.extract.return_value = [confirmation]

    result = extract_information(
        _context(extractor),
        _state(
            parsed_message=original,
            translated_message=translated,
            expected_interaction=_expected(),
        ),
    )

    assert result["extracted_information"] == [confirmation]
    extractor.extract.assert_called_once_with(message=original)


def test_information_extractor_delegates_confirmation_to_qwen() -> None:
    extractor = InformationExtractor.__new__(InformationExtractor)
    extractor._inference_lock = Lock()
    extractor._max_tokens = 32
    extractor._model = Mock()
    extractor._model.create_chat_completion.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"confirmation":"yes"}',
                }
            }
        ]
    }

    result = extractor.extract(Message("ja"))

    assert len(result) == 1
    assert result[0].information_field is InformationField.CONFIRMATION
    assert result[0].content == "yes"
    extractor._model.create_chat_completion.assert_called_once()


def test_progress_preserves_confirmation_without_collecting_it() -> None:
    confirmation = _confirmation("yes")

    result = update_progress(
        _context(),
        _state(
            expected_interaction=_expected(),
            current_intent=Intent.BOOKING_REQUEST,
            detected_intent=Intent.UNKNOWN,
            extracted_information=[confirmation],
            translated_message=Message("I", original_content="ja"),
            collected_information={},
            unknown_counter=1,
        ),
    )

    assert result["extracted_information"] == [confirmation]
    assert result["collected_information"] == {}
    assert result["unknown_counter"] == 0


def test_confirmation_resolution_uses_extracted_model_result() -> None:
    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_expected(),
            extracted_information=[_confirmation("yes")],
            changed_fields=[],
        ),
    )

    assert result["confirmation_outcome"] is ConfirmationOutcome.CONFIRMED
    assert result["domain_operation"] is DomainOperation.CREATE_BOOKING


def test_multilingual_negative_model_result_declines_confirmation() -> None:
    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_expected(),
            extracted_information=[_confirmation("no")],
            changed_fields=[],
            collected_information={},
        ),
    )

    assert result["confirmation_outcome"] is ConfirmationOutcome.DECLINED
    assert result["action"] is Action.CONFIRMATION_DECLINED


def test_information_change_confirmation_uses_model_result() -> None:
    replacement = Information(InformationField.LAST_NAME, "Doe")

    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_expected(
                ExpectedInteractionKind.INFORMATION_CHANGE_CONFIRMATION
            ),
            extracted_information=[_confirmation("yes")],
            pending_information_changes={
                InformationField.LAST_NAME: replacement
            },
        ),
    )

    assert result["confirmation_outcome"] is (
        ConfirmationOutcome.INFORMATION_CHANGE_CONFIRMED
    )
    assert result["collected_information"] == {
        InformationField.LAST_NAME: replacement
    }


def test_translated_affirmative_is_not_used_without_model_confirmation() -> None:
    result = resolve_confirmation(
        _context(),
        _state(
            expected_interaction=_expected(),
            extracted_information=[],
            changed_fields=[],
            translated_message=Message("yes", original_content="vielleicht"),
            detected_intent=Intent.UNKNOWN,
            collected_information={},
        ),
    )

    assert result["confirmation_outcome"] is ConfirmationOutcome.UNCLEAR
    assert result["action"] is Action.ASK_FOR_CONFIRMATION


def test_confirmation_prompt_is_language_independent() -> None:
    prompt = " ".join(get_system_prompt().split())

    assert "The input may be in any language." in prompt
    assert 'Normalize an explicit acceptance to exactly "yes"' in prompt
    assert 'an explicit rejection to exactly "no"' in prompt
