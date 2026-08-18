"""Local M2M100 translation with fastText language identification."""

from collections import OrderedDict
from dataclasses import replace
from threading import Lock
from typing import Any

import fasttext  # type: ignore[import-untyped]
import torch
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

from configuration.application import ApplicationSettings
from conversation.entities.message import Message
from conversation.models.translation.interface import TranslatorInterface
from observability.log_messages import LOG_MSG

_SETTINGS = ApplicationSettings.get_settings()
_TRANSLATION_MODEL_DIR = _SETTINGS.translation_model
_LANGUAGE_MODEL_PATH = _SETTINGS.language_detector
_PROCESSING_UNIT = _SETTINGS.translation_processing_unit
_MAX_NEW_TOKENS = _SETTINGS.translation_max_new_tokens
_NUM_BEAMS = _SETTINGS.translation_num_beams
_TRANSLATION_CACHE_SIZE = _SETTINGS.translation_cache_size


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
        self._cache: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        print(f"{type(self).__name__} loaded")

    def translate(self, text: Message, target_lang: str, source_lang: str) -> Message:
        """Return a translated copy of ``text`` without mutating it."""

        normalized_target = self._require_supported_language(target_lang)
        normalized_source_lang = self._require_supported_language(source_lang)
        translated_content = self._translate_content(
            text.content,
            normalized_target,
            normalized_source_lang,
        )

        return replace(text, content=translated_content)

    def _translate_content(
        self,
        content: str,
        target_lang: str,
        source_lang: str,
    ) -> str:
        cache_key = (content, target_lang, source_lang)
        with self._inference_lock, torch.inference_mode():
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                return self._cache[cache_key]

            self._tokenizer.src_lang = source_lang
            tokenized_inputs = self._tokenizer(
                content,
                return_tensors="pt",
            )
            model_inputs: dict[str, torch.Tensor] = {}
            for key, value in tokenized_inputs.items():
                model_inputs[key] = value.to(_PROCESSING_UNIT)
            generated_tokens = self._model.generate(
                **model_inputs,
                forced_bos_token_id=self._tokenizer.get_lang_id(target_lang),
                max_new_tokens=_MAX_NEW_TOKENS,
                num_beams=_NUM_BEAMS,
                do_sample=False,
                early_stopping=False,
                use_cache=True,
            )
            decoded = self._tokenizer.batch_decode(
                generated_tokens,
                skip_special_tokens=True,
            )
            translated = decoded[0]
            if not isinstance(translated, str):
                raise TypeError("Translator returned non-textual content")
            self._cache[cache_key] = translated
            if len(self._cache) > _TRANSLATION_CACHE_SIZE:
                self._cache.popitem(last=False)
            return translated

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

    def warm_up(self) -> None:
        """Warm language detection and one CPU translation pass."""

        message = Message(content="Guten Morgen.")
        self.determine(message)
        self._translate_content(message.content, "en", "de")

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
