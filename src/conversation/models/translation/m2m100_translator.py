"""Local M2M100 translation with fastText language identification."""

from dataclasses import replace
from pathlib import Path
from threading import Lock
from typing import Any

import fasttext  # type: ignore[import-untyped]
import torch
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

from conversation.entities.message import Message
from conversation.models.translation.interface import TranslatorInterface

from configuration.application import ApplicationSettings
from observability.log_messages import LOG_MSG

_TRANSLATION_MODEL_DIR = ApplicationSettings.get_settings().translation_model
_LANGUAGE_MODEL_PATH = ApplicationSettings.get_settings().language_detector
_PROCESSING_UNIT  = ApplicationSettings.get_settings().translation_processing_unit


class UnsupportedLanguageError(ValueError):
    """Raised when M2M100 cannot translate a requested language."""

class M2M100Translator(TranslatorInterface):
    """Translate locally with M2M100 and detect languages with fastText."""

    def __init__(self) -> None:
        if not _TRANSLATION_MODEL_DIR.is_dir():
            raise FileNotFoundError(
                f"Translation model directory not found: {_TRANSLATION_MODEL_DIR}"
            )
        if not _LANGUAGE_MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Language identification model not found: {_LANGUAGE_MODEL_PATH}"
            )

        self._tokenizer = M2M100Tokenizer.from_pretrained(
            _TRANSLATION_MODEL_DIR,
            local_files_only=True,
        )
        self._model = M2M100ForConditionalGeneration.from_pretrained(
            _TRANSLATION_MODEL_DIR,
            local_files_only=True,
        )
        LOG_MSG.debug(f"Translator - CUDA available: {torch.cuda.is_available()}")
        LOG_MSG.debug(f"Translator - XPU available: {torch.xpu.is_available()}")
        self._model.to(_PROCESSING_UNIT)
        self._model.eval()
        self._language_detector = fasttext.load_model(str(_LANGUAGE_MODEL_PATH))
        self._inference_lock = Lock()

    def translate(self, text: Message, target_lang: str, source_lang: str) -> Message:
        """Return a translated copy of ``text`` without mutating it."""

        normalized_target = self._require_supported_language(target_lang)
        normalized_source_lang = self._require_supported_language(source_lang)

        with self._inference_lock, torch.inference_mode():
            self._tokenizer.src_lang = normalized_source_lang
            #model_inputs = self._tokenizer(text.content, return_tensors="pt")
            model_inputs = {
                key: value.to(_PROCESSING_UNIT)
                for key, value in self._tokenizer(
                    text.content,
                    return_tensors="pt",
                ).items()
            }
            generated_tokens = self._model.generate(
                **model_inputs,
                forced_bos_token_id=self._tokenizer.get_lang_id(normalized_target),
                max_new_tokens=256,
                do_sample=False,
            )
            translated_content = self._tokenizer.batch_decode(
                generated_tokens,
                skip_special_tokens=True,
            )[0]

        return replace(text, content=translated_content)

    def determine(self, text: Message) -> str:
        """Return the fastText language code for ``text.content``."""

        detector_input = " ".join(text.content.split())
        if not detector_input:
            raise ValueError("Cannot determine the language of an empty message")

        labels, _probabilities = self._language_detector.predict(detector_input, k=1)
        label = self._first_label(labels)
        prefix = "__label__"
        if not label.startswith(prefix):
            raise RuntimeError(f"Unexpected fastText language label: {label!r}")
        return label.removeprefix(prefix)

    def _require_supported_language(self, language: str) -> str:
        normalized = language.strip().lower()
        if normalized not in self._tokenizer.lang_code_to_id:
            raise UnsupportedLanguageError(
                f"Language code {language!r} is not supported by {_TRANSLATION_MODEL_DIR}"
            )
        return normalized

    @staticmethod
    def _first_label(labels: Any) -> str:
        if not labels:
            raise RuntimeError("fastText returned no language prediction")
        label = labels[0]
        if not isinstance(label, str):
            raise TypeError(f"Unexpected fastText language label: {label!r}")
        return label
