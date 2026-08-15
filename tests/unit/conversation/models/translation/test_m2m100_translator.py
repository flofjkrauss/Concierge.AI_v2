"""Unit tests for the M2M100 translation adapter without model inference."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from conversation.entities.message import Message
from conversation.models.translation import m2m100_translator as module
from conversation.models.translation.m2m100_translator import (
    M2M100Translator,
    UnsupportedLanguageError,
)


class _DeviceValue:
    def __init__(self) -> None:
        self.target: object | None = None

    def to(self, target: object) -> _DeviceValue:
        self.target = target
        return self


def _translator() -> tuple[M2M100Translator, Mock, Mock, Mock, _DeviceValue]:
    translator = M2M100Translator.__new__(M2M100Translator)
    tokenizer = Mock()
    model = Mock()
    detector = Mock()
    device_value = _DeviceValue()
    tokenizer.lang_code_to_id = {"de": 1, "en": 2}
    tokenizer.return_value = {"input_ids": device_value}
    tokenizer.get_lang_id.return_value = 2
    tokenizer.batch_decode.return_value = ["Good morning."]
    model.generate.return_value = object()
    detector.predict.return_value = (["__label__de"], [0.99])
    translator._tokenizer = tokenizer
    translator._model = model
    translator._language_detector = detector
    translator._inference_lock = Lock()
    translator._cache = OrderedDict()
    return translator, tokenizer, model, detector, device_value


def test_translate_preserves_message_metadata_and_caches_result() -> None:
    translator, tokenizer, model, _, device_value = _translator()
    source = Message("Guten Morgen.", message_id="message-1", language="de")

    first = translator.translate(source, target_lang=" EN ", source_lang="DE")
    second = translator.translate(source, target_lang="en", source_lang="de")

    assert first.content == "Good morning."
    assert first.message_id == source.message_id
    assert second.content == first.content
    assert model.generate.call_count == 1
    assert tokenizer.src_lang == "de"
    assert device_value.target == module._PROCESSING_UNIT


def test_translate_rejects_unsupported_language() -> None:
    translator, *_ = _translator()

    with pytest.raises(UnsupportedLanguageError, match="not supported"):
        translator.translate(Message("Hello"), "xx", "en")


def test_translate_rejects_non_textual_decoding() -> None:
    translator, tokenizer, *_ = _translator()
    tokenizer.batch_decode.return_value = [123]

    with pytest.raises(TypeError, match="non-textual"):
        translator.translate(Message("Hallo"), "en", "de")


def test_determine_normalizes_input_and_parses_fasttext_label() -> None:
    translator, _, _, detector, _ = _translator()

    assert translator.determine(Message("  Guten\nMorgen  ")) == "de"
    detector.predict.assert_called_once_with("Guten Morgen", k=1)


@pytest.mark.parametrize(
    ("labels", "error"),
    [([], RuntimeError), ([123], TypeError), (["de"], RuntimeError)],
)
def test_determine_rejects_invalid_fasttext_results(
    labels: list[object],
    error: type[Exception],
) -> None:
    translator, _, _, detector, _ = _translator()
    detector.predict.return_value = (labels, [])

    with pytest.raises(error):
        translator.determine(Message("Hallo"))


def test_determine_rejects_empty_message() -> None:
    translator, *_ = _translator()

    with pytest.raises(ValueError, match="empty message"):
        translator.determine(Message("   "))


def test_constructor_loads_local_dependencies(monkeypatch, tmp_path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    detector_path = tmp_path / "lid.bin"
    detector_path.write_bytes(b"model")
    tokenizer = Mock()
    model = Mock()
    detector = Mock()
    tokenizer_factory = Mock(return_value=tokenizer)
    model_factory = Mock(return_value=model)
    detector_factory = Mock(return_value=detector)
    monkeypatch.setattr(module, "_TRANSLATION_MODEL_DIR", model_dir)
    monkeypatch.setattr(module, "_LANGUAGE_MODEL_PATH", detector_path)
    monkeypatch.setattr(
        module,
        "M2M100Tokenizer",
        SimpleNamespace(from_pretrained=tokenizer_factory),
    )
    monkeypatch.setattr(
        module,
        "M2M100ForConditionalGeneration",
        SimpleNamespace(from_pretrained=model_factory),
    )
    monkeypatch.setattr(module.fasttext, "load_model", detector_factory)

    result = M2M100Translator()

    assert result._tokenizer is tokenizer
    assert result._model is model
    model.to.assert_called_once_with(module._PROCESSING_UNIT)
    model.eval.assert_called_once_with()
    detector_factory.assert_called_once_with(str(detector_path))


def test_constructor_requires_local_model_directory(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(module, "_TRANSLATION_MODEL_DIR", tmp_path / "missing")

    with pytest.raises(FileNotFoundError, match="model directory"):
        M2M100Translator()
