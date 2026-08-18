from collections import OrderedDict
from pathlib import Path
from threading import Lock

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from configuration.application import ApplicationSettings
from conversation.entities.message import Message
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.value_object.intent import Intent
from observability.log_messages import LOG_MSG
from observability.utils.to_json import to_jsonable

_SETTINGS = ApplicationSettings.get_settings()
_INTENT_CACHE_SIZE = _SETTINGS.intent_cache_size


class IntentClassifier(IntentionDetectorInterface):
    def __init__(
        self,
        model_path: str | Path | None = None,
        processing_unit: str | None = None,
    ) -> None:
        selected_model_path = model_path or _SETTINGS.intent_detection_model
        selected_processing_unit = processing_unit or _SETTINGS.intent_processing_unit
        self._device = torch.device(selected_processing_unit)

        self._tokenizer = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
            selected_model_path,
            local_files_only=True,
        )

        self._model = AutoModelForSequenceClassification.from_pretrained(
            selected_model_path,
            local_files_only=True,
        )

        self._model.to(self._device)
        self._model.eval()
        self._inference_lock = Lock()
        self._cache: OrderedDict[str, Intent] = OrderedDict()
        print(f"{type(self).__name__} loaded")

    def determine(self, message: Message) -> Intent:
        content = message.content
        with self._inference_lock:
            if content in self._cache:
                self._cache.move_to_end(content)
                return self._cache[content]

            intent = self._determine_content(content)
            self._cache[content] = intent
            if len(self._cache) > _INTENT_CACHE_SIZE:
                self._cache.popitem(last=False)
            return intent

    def warm_up(self) -> None:
        """Run one uncached inference before the service accepts guest turns."""

        with self._inference_lock:
            self._determine_content("Hello.")

    def _determine_content(self, content: str) -> Intent:
        inputs = self._tokenizer(
            content,
            return_tensors="pt",
            truncation=True,
            max_length=_SETTINGS.intent_max_tokens,
        )

        device_inputs: dict[str, torch.Tensor] = {}
        for key, value in inputs.items():
            device_inputs[key] = value.to(self._device)
        inputs = device_inputs

        with torch.inference_mode():
            logits = self._model(**inputs).logits

        probabilities = torch.softmax(logits, dim=-1)
        class_id = int(torch.argmax(probabilities, dim=-1).item())

        category = self._model.config.id2label[class_id]
        probability = float(probabilities[0, class_id].item())
        LOG_MSG.debug(
            f"Intent parsed from message: {content} with {probability} probability.",
            extra=to_jsonable(
                {
                    "intent": category,
                    "class_id": class_id,
                    "probability": probability,
                }
            ),
        )
        return Intent(category)
