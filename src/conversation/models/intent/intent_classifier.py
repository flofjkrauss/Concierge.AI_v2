from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from conversation.entities.message import Message
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.value_object.intent import Intent

from observability.log_messages import LOG_MSG
from observability.utils.to_json import to_jsonable

from configuration.application import ApplicationSettings


class IntentClassifier(IntentionDetectorInterface):
    def __init__(
        self,
        model_path: str | Path = ApplicationSettings.get_settings().intent_detection_model,
        processing_unit: str = ApplicationSettings.get_settings().intent_processing_unit
    ) -> None:
        self._device = torch.device(processing_unit)

        self._tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
        )

        self._model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            local_files_only=True,
        )

        self._model.to(self._device)
        self._model.eval()

    def determine(self, message: Message) -> Intent:

        
        inputs = self._tokenizer(
            message.content,
            return_tensors="pt",
            truncation=True,
        )
        
        inputs = {
            key: value.to(self._device)
            for key, value in inputs.items()
        }

        with torch.inference_mode():
            logits = self._model(**inputs).logits

        probabilities = torch.softmax(logits, dim=-1)
        class_id = int(torch.argmax(probabilities, dim=-1).item())

        category = self._model.config.id2label[class_id]
        probability = float(probabilities[0, class_id].item())
        print(f"Intent from '{message.content}': {category} with {probability:.4f}")
        LOG_MSG.debug(
        f"Intent parsed from message: {message.content}",
            extra=to_jsonable(
                {
                    "intent": category,
                    "class_id": class_id,
                    "probability": probability,
                }
            )
        )
        return Intent(category)