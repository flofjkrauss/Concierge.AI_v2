from __future__ import annotations

from datetime import date
from typing import cast
from unittest.mock import Mock

import pytest

from configuration.application import ApplicationSettings
from conversation.entities.information import Information
from conversation.entities.interaction_response import (
    EmptyInteractionResponse,
    ErrorResponse,
    InteractionResponse,
)
from conversation.entities.message import Message
from conversation.graph.nodes import ConversationNodes, nodes_from_settings
from conversation.graph.state import (
    ConfirmationOutcome,
    ConversationMessage,
    ConversationState,
    DomainOperation,
    ExpectedInteraction,
    ExpectedInteractionKind,
    MessageRole,
)
from conversation.information_extrator import InformationExtractor
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.models.translation.interface import TranslatorInterface
from conversation.user_interaction import UserInteraction
from conversation.value_object.action import Action
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent
from domain.entities.booking import Booking


def graph_state(**values: object) -> ConversationState:
    return cast(ConversationState, values)


def make_nodes() -> tuple[ConversationNodes, Mock, Mock, Mock, Mock, Mock]:
    translator = Mock(spec=TranslatorInterface)
    classifier = Mock(spec=IntentionDetectorInterface)
    extractor = Mock(spec=InformationExtractor)
    interaction = Mock(spec=UserInteraction)
    adapter = Mock()
    nodes = ConversationNodes(
        translator=translator,
        intent_classifier=classifier,
        information_extractor=extractor,
        user_interaction=interaction,
        domain_adapter=adapter,
        domain_language="en",
        max_unknown_messages=2,
    )
    return nodes, translator, classifier, extractor, interaction, adapter


def expected_confirmation(
    *,
    intent: Intent = Intent.BOOKING_REQUEST,
    operation: DomainOperation = DomainOperation.CREATE_BOOKING,
) -> ExpectedInteraction:
    return ExpectedInteraction(
        ExpectedInteractionKind.BOOKING_CONFIRMATION,
        intent,
        operation,
    )


def test_begin_turn_initializes_new_thread() -> None:
    nodes, _, _, _, interaction, _ = make_nodes()
    response = InteractionResponse(True, "session-1")
    interaction.display_greeting.return_value = response

    result = nodes.begin_turn(graph_state(session_id="session-1", language=None))

    assert result["initialized"] is True
    assert result["session_active"] is True
    assert result["current_intent"] is Intent.CONVERSATION_INITIATION
    assert result["response"] is response
    assert result["message_history"] == []
    assert result["collected_information"] == {}
    interaction.display_greeting.assert_called_once_with(
        intent=Intent.CONVERSATION_INITIATION,
        data="session-1",
    )


def test_begin_turn_requires_session_id_for_new_thread() -> None:
    nodes, *_ = make_nodes()

    with pytest.raises(ValueError, match="requires a session_id"):
        nodes.begin_turn(graph_state())


def test_begin_turn_returns_empty_response_for_blank_message() -> None:
    nodes, _, _, _, interaction, _ = make_nodes()
    empty = EmptyInteractionResponse()
    interaction.send_empty_response.return_value = empty

    result = nodes.begin_turn(graph_state(initialized=True, incoming_message="   "))

    assert result["response"] is empty
    assert result["parsed_message"] is None


def test_begin_turn_returns_error_for_rejected_message() -> None:
    nodes, _, _, _, interaction, _ = make_nodes()
    error = ErrorResponse(False, "Error", "Invalid message")
    interaction.parse_message.return_value = None
    interaction.send_error_msg.return_value = error

    result = nodes.begin_turn(
        graph_state(initialized=True, incoming_message="too long")
    )

    assert result["response"] is error
    assert result["session_active"] is False


def test_begin_turn_keeps_valid_parsed_message() -> None:
    nodes, _, _, _, interaction, _ = make_nodes()
    message = Message("Hello")
    interaction.parse_message.return_value = message

    result = nodes.begin_turn(graph_state(initialized=True, incoming_message="Hello"))

    assert result["parsed_message"] is message


def test_translate_input_detects_and_translates_foreign_language() -> None:
    nodes, translator, *_ = make_nodes()
    parsed = Message("Hallo")
    translated = Message("Hello")
    translator.determine.return_value = "de"
    translator.translate.return_value = translated

    result = nodes.translate_input(graph_state(parsed_message=parsed, language=None))

    assert result["language"] == "de"
    assert result["translated_message"].content == "Hello"  # type: ignore[union-attr]
    assert result["translated_message"].language == "de"  # type: ignore[union-attr]
    translator.translate.assert_called_once_with(parsed, target_lang="en")


def test_translate_input_uses_domain_language_when_detection_is_empty() -> None:
    nodes, translator, *_ = make_nodes()
    parsed = Message("Hello")
    translator.determine.return_value = "  "

    result = nodes.translate_input(graph_state(parsed_message=parsed, language=None))

    assert result["language"] == "en"
    translator.translate.assert_not_called()


def test_translate_input_reuses_known_language() -> None:
    nodes, translator, *_ = make_nodes()
    parsed = Message("Hello")

    result = nodes.translate_input(graph_state(parsed_message=parsed, language="en"))

    assert result["translated_message"] == parsed
    translator.determine.assert_not_called()
    translator.translate.assert_not_called()


def test_translate_input_requires_parsed_message() -> None:
    nodes, *_ = make_nodes()

    with pytest.raises(TypeError, match="parsed_message must contain a Message"):
        nodes.translate_input(graph_state(parsed_message=None))


def test_store_user_message_marks_role() -> None:
    nodes, *_ = make_nodes()
    message = Message("Hello")

    result = nodes.store_user_message(graph_state(translated_message=message))

    assert result == {
        "message_history": [ConversationMessage(MessageRole.USER, message)]
    }


def test_classifier_receives_history_and_current_message() -> None:
    nodes, _, classifier, *_ = make_nodes()
    previous = ConversationMessage(MessageRole.ASSISTANT, Message("Welcome"))
    current = Message("Book a room", message_id="current")
    current_entry = ConversationMessage(MessageRole.USER, current)
    classifier.determine.return_value = Intent.BOOKING_REQUEST

    result = nodes.classify_intent(
        graph_state(
            translated_message=current,
            message_history=[previous, current_entry],
        )
    )

    model_message = classifier.determine.call_args.kwargs["message"]
    assert "Assistant: Welcome" in model_message.content
    assert "Current user message:\nBook a room" in model_message.content
    assert model_message.content.count("Book a room") == 1
    assert result["detected_intent"] is Intent.BOOKING_REQUEST


def test_extractor_receives_current_translated_message() -> None:
    nodes, _, _, extractor, *_ = make_nodes()
    current = Message("Tomorrow")
    information = Information(InformationField.FIRST_NAME, "Alex")
    extractor.extract.return_value = [information]

    result = nodes.extract_information(
        graph_state(translated_message=current, message_history=[])
    )

    assert result["extracted_information"] == [information]
    extractor.extract.assert_called_once_with(message=current)


def test_update_progress_increments_consecutive_unknown_counter() -> None:
    nodes, *_ = make_nodes()

    result = nodes.update_progress(
        graph_state(
            detected_intent=Intent.UNKNOWN,
            extracted_information=[],
            unknown_counter=2,
        )
    )

    assert result["unknown_counter"] == 3
    assert result["termination_requested"] is True


def test_update_progress_resets_counter_and_indexes_information() -> None:
    nodes, *_ = make_nodes()
    information = Information(InformationField.FIRST_NAME, "Alex")

    result = nodes.update_progress(
        graph_state(
            detected_intent=Intent.UNKNOWN,
            extracted_information=[information],
            unknown_counter=2,
        )
    )

    assert result["unknown_counter"] == 0
    assert result["collected_information"] == {InformationField.FIRST_NAME: information}


def test_update_progress_does_not_count_recognized_confirmation() -> None:
    nodes, *_ = make_nodes()

    result = nodes.update_progress(
        graph_state(
            detected_intent=Intent.UNKNOWN,
            extracted_information=[],
            unknown_counter=1,
            expected_interaction=expected_confirmation(),
            translated_message=Message("Yes."),
        )
    )

    assert result["unknown_counter"] == 0


def test_resolve_confirmation_accepts_normalized_affirmative_reply() -> None:
    nodes, *_ = make_nodes()
    expected = expected_confirmation()

    result = nodes.resolve_confirmation(
        graph_state(
            expected_interaction=expected,
            extracted_information=[],
            translated_message=Message("  YES!  "),
        )
    )

    assert result["confirmation_outcome"] is ConfirmationOutcome.CONFIRMED
    assert result["domain_operation"] is DomainOperation.CREATE_BOOKING
    assert result["expected_interaction"] is None


def test_resolve_confirmation_handles_decline() -> None:
    nodes, *_ = make_nodes()

    result = nodes.resolve_confirmation(
        graph_state(
            expected_interaction=expected_confirmation(),
            extracted_information=[],
            translated_message=Message("No thanks"),
        )
    )

    assert result["confirmation_outcome"] is ConfirmationOutcome.DECLINED
    assert result["action"] is Action.ASK_INTENT
    assert result["last_intent_fulfilled"] is True


def test_resolve_confirmation_returns_to_fields_when_required_data_changed() -> None:
    nodes, *_ = make_nodes()
    changed = Information(InformationField.CHECK_IN, date(2030, 7, 1))

    result = nodes.resolve_confirmation(
        graph_state(
            expected_interaction=expected_confirmation(),
            extracted_information=[changed],
        )
    )

    assert result["confirmation_outcome"] is ConfirmationOutcome.CHANGED
    assert result["current_intent"] is Intent.BOOKING_REQUEST


def test_resolve_confirmation_allows_different_intent_to_interrupt() -> None:
    nodes, *_ = make_nodes()

    result = nodes.resolve_confirmation(
        graph_state(
            expected_interaction=expected_confirmation(),
            extracted_information=[],
            translated_message=Message("What time is breakfast?"),
            detected_intent=Intent.INFORMATION_REQUEST,
        )
    )

    assert result["confirmation_outcome"] is ConfirmationOutcome.INTERRUPTED
    assert result["expected_interaction"] is None


def test_resolve_confirmation_repeats_prompt_for_unclear_reply() -> None:
    nodes, *_ = make_nodes()
    collected = {
        InformationField.FIRST_NAME: Information(
            InformationField.FIRST_NAME,
            "Alex",
        )
    }

    result = nodes.resolve_confirmation(
        graph_state(
            expected_interaction=expected_confirmation(),
            extracted_information=[],
            translated_message=Message("Maybe"),
            detected_intent=Intent.UNKNOWN,
            collected_information=collected,
        )
    )

    assert result["confirmation_outcome"] is ConfirmationOutcome.UNCLEAR
    assert result["action"] is Action.ASK_FOR_CONFIRMATION
    assert result["domain_data"] == collected


def test_resolve_confirmation_requires_pending_interaction() -> None:
    nodes, *_ = make_nodes()

    with pytest.raises(ValueError, match="No confirmation is pending"):
        nodes.resolve_confirmation(graph_state(expected_interaction=None))


def test_activate_intent_greets_conversation_initiation() -> None:
    nodes, *_ = make_nodes()

    assert nodes.activate_intent(
        graph_state(detected_intent=Intent.CONVERSATION_INITIATION)
    ) == {"action": Action.DISPLAY_GREETING, "domain_data": None}


def test_activate_intent_switches_to_detected_business_intent() -> None:
    nodes, *_ = make_nodes()

    result = nodes.activate_intent(
        graph_state(
            detected_intent=Intent.BOOKING_CHECK,
            current_intent=Intent.AVAILABILITY_CHECK,
        )
    )

    assert result == {
        "current_intent": Intent.BOOKING_CHECK,
        "last_intent_fulfilled": False,
    }


def test_activate_intent_keeps_open_intent_for_unknown_message() -> None:
    nodes, *_ = make_nodes()

    result = nodes.activate_intent(
        graph_state(
            detected_intent=Intent.UNKNOWN,
            current_intent=Intent.AVAILABILITY_CHECK,
            last_intent_fulfilled=False,
            extracted_information=[],
        )
    )

    assert result["current_intent"] is Intent.AVAILABILITY_CHECK


def test_activate_intent_resumes_fulfilled_intent_when_relevant_data_changes() -> None:
    nodes, *_ = make_nodes()
    changed = Information(InformationField.GUEST_COUNT, 3)

    result = nodes.activate_intent(
        graph_state(
            detected_intent=Intent.UNKNOWN,
            current_intent=Intent.AVAILABILITY_CHECK,
            last_intent_fulfilled=True,
            extracted_information=[changed],
        )
    )

    assert result["current_intent"] is Intent.AVAILABILITY_CHECK
    assert result["last_intent_fulfilled"] is False


def test_activate_intent_asks_for_new_intent_after_completed_work() -> None:
    nodes, *_ = make_nodes()

    assert nodes.activate_intent(
        graph_state(
            detected_intent=Intent.UNKNOWN,
            current_intent=Intent.AVAILABILITY_CHECK,
            last_intent_fulfilled=True,
            extracted_information=[],
        )
    ) == {"action": Action.ASK_INTENT, "domain_data": None}


def test_determine_missing_fields_uses_valid_collected_information() -> None:
    nodes, *_ = make_nodes()
    information = {
        InformationField.CHECK_IN: Information(
            InformationField.CHECK_IN,
            date(2030, 6, 10),
        ),
        InformationField.GUEST_COUNT: Information(
            InformationField.GUEST_COUNT,
            2,
        ),
    }

    result = nodes.determine_missing_fields(
        graph_state(
            current_intent=Intent.AVAILABILITY_CHECK,
            collected_information=information,
        )
    )

    assert result["missing_fields"] == [
        InformationField.CHECK_OUT,
        InformationField.ACCESSIBLE,
    ]


def test_determine_action_requests_missing_fields() -> None:
    nodes, *_ = make_nodes()

    result = nodes.determine_action(
        graph_state(missing_fields=[InformationField.EMAIL])
    )

    assert result == {
        "action": Action.ASK_FOR_DATA,
        "domain_data": [InformationField.EMAIL],
        "last_intent_fulfilled": False,
    }


@pytest.mark.parametrize(
    ("intent", "operation"),
    [
        (Intent.AVAILABILITY_CHECK, DomainOperation.FIND_AVAILABILITY),
        (Intent.BOOKING_CHECK, DomainOperation.GET_BOOKING),
        (Intent.INFORMATION_REQUEST, DomainOperation.GET_INFORMATION),
        (Intent.BOOKING_CANCELLATION, DomainOperation.GET_BOOKING),
    ],
)
def test_determine_action_selects_immediate_domain_operation(
    intent: Intent,
    operation: DomainOperation,
) -> None:
    nodes, *_ = make_nodes()

    assert nodes.determine_action(
        graph_state(current_intent=intent, missing_fields=[])
    ) == {"domain_operation": operation}


@pytest.mark.parametrize(
    ("intent", "kind", "operation"),
    [
        (
            Intent.BOOKING_REQUEST,
            ExpectedInteractionKind.BOOKING_CONFIRMATION,
            DomainOperation.CREATE_BOOKING,
        ),
    ],
)
def test_determine_action_requires_confirmation_for_side_effects(
    intent: Intent,
    kind: ExpectedInteractionKind,
    operation: DomainOperation,
) -> None:
    nodes, *_ = make_nodes()

    result = nodes.determine_action(
        graph_state(
            current_intent=intent,
            missing_fields=[],
            collected_information={},
        )
    )

    assert result["action"] is Action.ASK_FOR_CONFIRMATION
    expected = result["expected_interaction"]
    assert expected.kind is kind  # type: ignore[union-attr]
    assert expected.operation is operation  # type: ignore[union-attr]


def test_determine_action_asks_for_intent_when_none_is_actionable() -> None:
    nodes, *_ = make_nodes()

    assert nodes.determine_action(
        graph_state(
            current_intent=Intent.UNKNOWN,
            missing_fields=[],
        )
    ) == {"action": Action.ASK_INTENT, "domain_data": None}


def test_execute_domain_action_delegates_and_selects_response_action() -> None:
    nodes, _, _, _, _, adapter = make_nodes()
    adapter.execute.return_value = ["room"]
    collected = {}

    result = nodes.execute_domain_action(
        graph_state(
            domain_operation=DomainOperation.FIND_AVAILABILITY,
            collected_information=collected,
        )
    )

    adapter.execute.assert_called_once_with(
        operation=DomainOperation.FIND_AVAILABILITY,
        information=collected,
    )
    assert result["action"] is Action.DISPLAY_AVAILABILITY
    assert result["domain_data"] == ["room"]
    assert result["last_intent_fulfilled"] is True


def test_execute_domain_action_requires_confirmation_after_booking_lookup(
    booking: Booking,
) -> None:
    nodes, _, _, _, _, adapter = make_nodes()
    adapter.execute.return_value = booking

    result = nodes.execute_domain_action(
        graph_state(
            domain_operation=DomainOperation.GET_BOOKING,
            current_intent=Intent.BOOKING_CANCELLATION,
            collected_information={},
        )
    )

    assert result["action"] is Action.ASK_FOR_CONFIRMATION
    assert result["domain_data"] is booking
    expected = result["expected_interaction"]
    assert expected.kind is ExpectedInteractionKind.CANCELLATION_CONFIRMATION  # type: ignore[union-attr]
    assert expected.operation is DomainOperation.CANCEL_BOOKING  # type: ignore[union-attr]
    assert result["last_intent_fulfilled"] is False


def test_execute_domain_action_handles_missing_booking_for_cancellation() -> None:
    nodes, _, _, _, _, adapter = make_nodes()
    adapter.execute.return_value = None

    result = nodes.execute_domain_action(
        graph_state(
            domain_operation=DomainOperation.GET_BOOKING,
            current_intent=Intent.BOOKING_CANCELLATION,
            collected_information={},
        )
    )

    assert result == {
        "domain_operation": None,
        "domain_data": None,
        "action": Action.DISPLAY_BOOKING,
        "last_intent_fulfilled": False,
    }


def test_execute_domain_action_converts_expected_error_to_response() -> None:
    nodes, _, _, _, interaction, adapter = make_nodes()
    adapter.execute.side_effect = ValueError("invalid data")
    error = ErrorResponse(False, "Error", "invalid data")
    interaction.send_error_msg.return_value = error

    result = nodes.execute_domain_action(
        graph_state(
            domain_operation=DomainOperation.GET_BOOKING,
            collected_information={},
        )
    )

    assert result["response"] is error
    assert result["session_active"] is False
    assert result["last_intent_fulfilled"] is False


def test_execute_domain_action_requires_operation() -> None:
    nodes, *_ = make_nodes()

    with pytest.raises(ValueError, match="No domain operation was selected"):
        nodes.execute_domain_action(graph_state(domain_operation=None))


def test_build_response_preserves_existing_response() -> None:
    nodes, *_ = make_nodes()

    assert (
        nodes.build_response(
            graph_state(response=InteractionResponse(True, "Existing"))
        )
        == {}
    )


def test_build_response_delegates_to_user_interaction() -> None:
    nodes, _, _, _, interaction, _ = make_nodes()
    response = InteractionResponse(True, "Result")
    interaction.build_response.return_value = response

    result = nodes.build_response(
        graph_state(
            response=None,
            action=Action.DISPLAY_BOOKING,
            current_intent=Intent.BOOKING_CHECK,
            domain_data="booking",
        )
    )

    interaction.build_response.assert_called_once_with(
        action=Action.DISPLAY_BOOKING,
        intent=Intent.BOOKING_CHECK,
        data="booking",
    )
    assert result["response"] is response
    assert result["response_in_domain_language"] == "Result"


def test_build_response_requires_action() -> None:
    nodes, *_ = make_nodes()

    with pytest.raises(ValueError, match="requires an action"):
        nodes.build_response(graph_state(response=None, action=None))


def test_terminate_conversation_closes_session() -> None:
    nodes, _, _, _, interaction, _ = make_nodes()
    response = ErrorResponse(False, "Error", "threshold")
    interaction.send_error_msg.return_value = response

    result = nodes.terminate_conversation(graph_state())

    assert result["response"] is response
    assert result["session_active"] is False
    assert result["expected_interaction"] is None


def test_translate_response_skips_empty_or_domain_language_response() -> None:
    nodes, translator, *_ = make_nodes()

    assert nodes.translate_response(graph_state(response=None)) == {}
    assert (
        nodes.translate_response(
            graph_state(response=InteractionResponse(True, "Hello"), language="en")
        )
        == {}
    )
    translator.translate.assert_not_called()


def test_translate_response_returns_translated_copy() -> None:
    nodes, translator, *_ = make_nodes()
    response = InteractionResponse(True, "Hello")
    translator.translate.return_value = Message("Hallo")

    result = nodes.translate_response(graph_state(response=response, language="de"))

    translated = result["response"]
    assert translated.text == "Hallo"  # type: ignore[union-attr]
    assert response.text == "Hello"


def test_store_assistant_message_preserves_domain_and_display_text() -> None:
    nodes, *_ = make_nodes()
    response = InteractionResponse(True, "Hallo")

    result = nodes.store_assistant_message(
        graph_state(
            response=response,
            response_in_domain_language="Hello",
            language="de",
        )
    )

    entry = result["message_history"][0]  # type: ignore[index]
    assert entry.role is MessageRole.ASSISTANT
    assert entry.message.content == "Hello"
    assert entry.message.original_content == "Hallo"
    assert entry.message.language == "de"


def test_store_assistant_message_skips_missing_or_empty_response() -> None:
    nodes, *_ = make_nodes()

    assert nodes.store_assistant_message(graph_state(response=None)) == {}
    assert (
        nodes.store_assistant_message(
            graph_state(response=InteractionResponse(True, ""))
        )
        == {}
    )


def test_write_state_to_logs_serializes_state(monkeypatch) -> None:
    nodes, *_ = make_nodes()
    debug = Mock()
    monkeypatch.setattr("conversation.graph.nodes.LOG_MSG.debug", debug)
    state = graph_state(initialized=True, current_intent=Intent.BOOKING_CHECK)

    assert nodes.write_state_to_logs(state) == {"initialized": True}
    assert debug.call_args.args == ("Conversation message processed",)
    assert debug.call_args.kwargs["extra"]["conversation_state"] == {
        "initialized": True,
        "current_intent": "booking_check",
    }


def test_nodes_from_settings_uses_application_defaults() -> None:
    translator = Mock(spec=TranslatorInterface)
    classifier = Mock(spec=IntentClassifier)
    extractor = Mock(spec=InformationExtractor)
    interaction = Mock(spec=UserInteraction)
    adapter = Mock()

    nodes = nodes_from_settings(
        translator=translator,
        intent_classifier=classifier,
        information_extractor=extractor,
        user_interaction=interaction,
        domain_adapter=adapter,
    )

    settings = ApplicationSettings.get_settings()
    assert nodes.domain_language == settings.domain_language
    assert nodes.max_unknown_messages == settings.max_num_msg_with_intent_unknown
