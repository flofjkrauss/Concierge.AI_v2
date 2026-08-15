"""Unit tests for the local intent-classification adapter."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock

from conversation.entities.message import Message
from conversation.models.intent import intent_classifier as classifier_module
from conversation.models.intent.intent_classifier import IntentClassifier
from conversation.value_object.intent import Intent


class _DeviceValue:
    def __init__(self) -> None:
        self.target: object | None = None

    def to(self, target: object) -> _DeviceValue:
        self.target = target
        return self


class _Scalar:
    def __init__(self, value: float) -> None:
        self.value = value

    def item(self) -> int | float:
        return self.value


class _Probabilities:
    def __getitem__(self, index: tuple[int, int]) -> _Scalar:
        assert index == (0, 1)
        return _Scalar(0.91)


def _empty_classifier() -> IntentClassifier:
    classifier = IntentClassifier.__new__(IntentClassifier)
    classifier._inference_lock = Lock()
    classifier._cache = OrderedDict()
    return classifier


def test_determine_caches_classification_by_message_content(
    monkeypatch,
) -> None:
    classifier = _empty_classifier()
    determine_content = Mock(return_value=Intent.BOOKING_REQUEST)
    monkeypatch.setattr(classifier, "_determine_content", determine_content)

    first = classifier.determine(Message("Book a room"))
    second = classifier.determine(Message("Book a room"))

    assert first is Intent.BOOKING_REQUEST
    assert second is Intent.BOOKING_REQUEST
    determine_content.assert_called_once_with("Book a room")


def test_determine_evicts_oldest_cached_message(monkeypatch) -> None:
    classifier = _empty_classifier()
    monkeypatch.setattr(classifier_module, "_INTENT_CACHE_SIZE", 2)
    monkeypatch.setattr(
        classifier,
        "_determine_content",
        lambda content: Intent.UNKNOWN,
    )

    for content in ("one", "two", "three"):
        classifier.determine(Message(content))

    assert list(classifier._cache) == ["two", "three"]


def test_determine_content_maps_highest_model_label(monkeypatch) -> None:
    classifier = _empty_classifier()
    input_value = _DeviceValue()
    classifier._device = "cpu"
    classifier._tokenizer = Mock(return_value={"input_ids": input_value})
    classifier._model = Mock()
    classifier._model.return_value = SimpleNamespace(logits=object())
    classifier._model.config.id2label = {1: Intent.BOOKING_REQUEST.value}
    monkeypatch.setattr(
        classifier_module.torch,
        "softmax",
        lambda logits, dim: _Probabilities(),
    )
    monkeypatch.setattr(
        classifier_module.torch,
        "argmax",
        lambda probabilities, dim: _Scalar(1),
    )

    result = classifier._determine_content("Book a room")

    assert result is Intent.BOOKING_REQUEST
    assert input_value.target == "cpu"
    classifier._model.assert_called_once_with(input_ids=input_value)


def test_warm_up_does_not_populate_request_cache(monkeypatch) -> None:
    classifier = _empty_classifier()
    determine_content = Mock(return_value=Intent.UNKNOWN)
    monkeypatch.setattr(classifier, "_determine_content", determine_content)

    classifier.warm_up()

    determine_content.assert_called_once_with("Hello.")
    assert classifier._cache == {}
