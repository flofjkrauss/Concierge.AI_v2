"""Unit tests for the local information-extraction adapter."""

from datetime import date
from threading import Lock
from unittest.mock import Mock

import pytest

from conversation.entities.message import Message
from conversation.models.information.information_extrator import InformationExtractor
from conversation.value_object.information_fields import InformationField


def _extractor_with_response(content: object) -> InformationExtractor:
    extractor = InformationExtractor.__new__(InformationExtractor)
    extractor._inference_lock = Lock()
    extractor._max_tokens = 64
    extractor._model = Mock()
    extractor._model.create_chat_completion.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return extractor


def test_extract_converts_valid_fields_and_ignores_invalid_values() -> None:
    extractor = _extractor_with_response(
        '{"first_name":"Alex","check_in":"2030-06-10",'
        '"guest_count":0,"unknown":"value"}'
    )

    result = extractor.extract(Message("My name is Alex and I arrive June 10."))

    assert [(item.information_field, item.content) for item in result] == [
        (InformationField.FIRST_NAME, "Alex"),
        (InformationField.CHECK_IN, date(2030, 6, 10)),
    ]
    extractor._model.create_chat_completion.assert_called_once()


def test_extract_rejects_non_textual_model_content() -> None:
    extractor = _extractor_with_response(None)

    with pytest.raises(TypeError, match="no textual content"):
        extractor.extract(Message("Hello"))


def test_extract_propagates_invalid_json() -> None:
    extractor = _extractor_with_response("not-json")

    with pytest.raises(ValueError):
        extractor.extract(Message("Hello"))


def test_warm_up_runs_representative_extraction() -> None:
    extractor = InformationExtractor.__new__(InformationExtractor)
    extractor.extract = Mock(return_value=[])

    extractor.warm_up()

    message = extractor.extract.call_args.args[0]
    assert message.content == "I would like to check availability."
