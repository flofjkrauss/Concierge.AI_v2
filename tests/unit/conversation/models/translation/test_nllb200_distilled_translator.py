"""Unit tests for the NLLB translation adapter without model inference."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from conversation.entities.message import Message
from conversation.models.translation import nllb200_distilled_translator as module
from conversation.models.translation.nllb200_distilled_translator import (
    NLLBTranslator,
    UnsupportedLanguageError,
)


class _DeviceValue:
    def to(self, target: object) -> _DeviceValue:
        return self


def _translator() -> tuple[NLLBTranslator, Mock, Mock, Mock]:
    translator = NLLBTranslator.__new__(NLLBTranslator)
    tokenizer = Mock()
    model = Mock()
    detector = Mock()
    tokenizer.unk_token_id = -1
    tokenizer.convert_tokens_to_ids.side_effect = lambda code: {
        "eng_Latn": 1,
        "deu_Latn": 2,
    }.get(code, -1)
    tokenizer.return_value = {"input_ids": _DeviceValue()}
    tokenizer.encode.return_value = [10, 11]
    tokenizer.batch_decode.return_value = ["Good morning."]
    model.generate.return_value = object()
    detector.predict.return_value = (["__label__de"], [0.99])
    translator._tokenizer = tokenizer
    translator._model = model
    translator._language_detector = detector
    translator._inference_lock = Lock()
    translator._cache = OrderedDict()
    return translator, tokenizer, model, detector


def test_translate_maps_language_codes_and_reuses_cache() -> None:
    translator, tokenizer, model, _ = _translator()
    source = Message("Guten Morgen.", message_id="message-1", language="de")

    first = translator.translate(source, target_lang="en", source_lang="de")
    second = translator.translate(source, target_lang="en", source_lang="de")

    assert first.content == "Good morning."
    assert first.message_id == source.message_id
    assert second.content == first.content
    assert tokenizer.src_lang == "deu_Latn"
    assert model.generate.call_count == 1
    assert model.generate.call_args.kwargs["forced_bos_token_id"] == 1


def test_single_token_translation_uses_small_generation_budget() -> None:
    translator, tokenizer, model, _ = _translator()
    tokenizer.encode.return_value = [10]

    translator.translate(Message("Hallo"), target_lang="en", source_lang="de")

    assert model.generate.call_args.kwargs["max_new_tokens"] == 2


@pytest.mark.parametrize("language", ["xx", "", "unknown"])
def test_translate_rejects_unknown_language(language: str) -> None:
    translator, *_ = _translator()

    with pytest.raises(UnsupportedLanguageError):
        translator.translate(Message("Hello"), language, "en")


def test_translate_rejects_unknown_tokenizer_language_id() -> None:
    translator, tokenizer, *_ = _translator()
    tokenizer.convert_tokens_to_ids.return_value = tokenizer.unk_token_id
    tokenizer.convert_tokens_to_ids.side_effect = None

    with pytest.raises(UnsupportedLanguageError, match="NLLB language code"):
        translator.translate(Message("Hello"), "en", "de")


@pytest.mark.parametrize(
    ("decoded", "error"),
    [([], RuntimeError), ([123], TypeError)],
)
def test_translate_rejects_invalid_decoding(
    decoded: list[object],
    error: type[Exception],
) -> None:
    translator, tokenizer, *_ = _translator()
    tokenizer.batch_decode.return_value = decoded

    with pytest.raises(error):
        translator.translate(Message("Hallo"), "en", "de")


def test_determine_and_warm_up_use_language_detector(monkeypatch) -> None:
    translator, _, _, detector = _translator()
    translate = Mock(return_value=Message("Good morning."))
    monkeypatch.setattr(translator, "translate", translate)

    assert translator.determine(Message(" Guten\nMorgen ")) == "de"
    translator.warm_up()

    assert detector.predict.call_count == 2
    translate.assert_called_once()


def test_constructor_loads_local_dependencies(monkeypatch, tmp_path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    detector_path = tmp_path / "lid.bin"
    detector_path.write_bytes(b"model")
    tokenizer = Mock()
    model = Mock()
    detector = Mock()
    monkeypatch.setattr(module, "_TRANSLATION_MODEL_DIR", model_dir)
    monkeypatch.setattr(module, "_LANGUAGE_MODEL_PATH", detector_path)
    monkeypatch.setattr(
        module,
        "AutoTokenizer",
        SimpleNamespace(from_pretrained=Mock(return_value=tokenizer)),
    )
    monkeypatch.setattr(
        module,
        "AutoModelForSeq2SeqLM",
        SimpleNamespace(from_pretrained=Mock(return_value=model)),
    )
    monkeypatch.setattr(module.fasttext, "load_model", Mock(return_value=detector))

    result = NLLBTranslator()

    assert result._tokenizer is tokenizer
    assert result._model is model
    model.to.assert_called_once_with(module._PROCESSING_UNIT)
    model.eval.assert_called_once_with()


def test_constructor_requires_language_detector_file(monkeypatch, tmp_path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    monkeypatch.setattr(module, "_TRANSLATION_MODEL_DIR", model_dir)
    monkeypatch.setattr(module, "_LANGUAGE_MODEL_PATH", tmp_path / "missing.bin")

    with pytest.raises(FileNotFoundError, match="identification model"):
        NLLBTranslator()
