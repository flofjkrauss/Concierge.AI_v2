"""Focused regression tests for translated graph responses."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from conversation.entities.interaction_response import (
    InformationResponse,
    InteractionResponse,
)
from conversation.entities.message import Message
from conversation.graph.nodes.translate_response import translate_response


@pytest.mark.parametrize(
    ("topic", "source_answer", "translated_answer"),
    [
        (
            "wifi",
            "Complimentary Wi-Fi is available throughout the hotel.",
            "Kostenloses WLAN ist im gesamten Hotel verfuegbar.",
        ),
        (
            "breakfast",
            "Breakfast is served daily from 7:00 to 10:30.",
            "Das Fruehstueck wird taeglich von 7:00 bis 10:30 serviert.",
        ),
    ],
)
def test_information_translation_preserves_canonical_topic(
    topic: str,
    source_answer: str,
    translated_answer: str,
) -> None:
    translator = Mock()
    translator.translate.return_value = Message(translated_answer)
    context = SimpleNamespace(translator=translator, domain_language="en")
    response = InformationResponse(
        session_active=True,
        text=f"({topic}){source_answer}",
    )

    result = translate_response(
        context,
        {"response": response, "language": "de"},
    )

    translator.translate.assert_called_once()
    assert translator.translate.call_args.args[0].content == source_answer
    assert result["response"].text == f"({topic}){translated_answer}"
    assert response.text == f"({topic}){source_answer}"


def test_multisentence_response_is_translated_without_dropping_question() -> None:
    translator = Mock()
    translator.translate.side_effect = [
        Message("Um Buchungsoptionen anzubieten, brauche ich weitere Angaben."),
        Message("Bitte teilen Sie mir mit: Wie viele Personen sind Sie?"),
    ]
    context = SimpleNamespace(translator=translator, domain_language="en")
    response = InteractionResponse(
        session_active=True,
        text=(
            "To offer possible booking options, I need to collect additional data. "
            "Please tell me: How many people are you?"
        ),
    )

    result = translate_response(
        context,
        {"response": response, "language": "de"},
    )

    assert [
        call.args[0].content for call in translator.translate.call_args_list
    ] == [
        "To offer possible booking options, I need to collect additional data.",
        "Please tell me: How many people are you?",
    ]
    assert result["response"].text == (
        "Um Buchungsoptionen anzubieten, brauche ich weitere Angaben. "
        "Bitte teilen Sie mir mit: Wie viele Personen sind Sie?"
    )
