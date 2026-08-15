import json
from datetime import UTC, date, datetime
from threading import Lock
from typing import Any, cast

from llama_cpp import Llama
from llama_cpp.llama_types import CreateChatCompletionResponse

from configuration.application import ApplicationSettings
from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.models.information.information_extraction_schema import (
    get_field_map,
    get_information_extraction_schema,
)
from conversation.models.information.information_extraction_system_prompt import (
    get_system_prompt,
)
from conversation.models.information.interface import InformationExtractorInterface
from conversation.value_object.information_fields import InformationField
from observability.log_messages import LOG_MSG


class InformationExtractor(InformationExtractorInterface):

    _SCHEMA = get_information_extraction_schema()
    _FIELD_MAP = get_field_map()
    _SYSTEM_PROMPT = get_system_prompt()

    def __init__(self) -> None:
        settings = ApplicationSettings.get_settings()
        self._model = Llama(
            model_path=str(settings.information_extraction_model),
            n_ctx=settings.information_context_tokens,
            n_batch=settings.information_batch_tokens,
            n_ubatch=settings.information_batch_tokens,
            n_threads=settings.information_generation_threads,
            n_threads_batch=settings.information_batch_threads,
            n_gpu_layers=0,
            use_mmap=True,
            verbose=False,
        )
        self._max_tokens = settings.information_max_tokens
        self._inference_lock = Lock()
        print(f"{type(self).__name__} loaded")

    def extract(self, message: Message) -> list[Information]:
        """Try to extract information fields from given user message."""
        with self._inference_lock:
            response = cast(
                CreateChatCompletionResponse,
                self._model.create_chat_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": self._SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": (
                                "Current date: "
                                f"{datetime.now(UTC).astimezone().date().isoformat()}"
                                f"\n\nUser message:\n{message.content}"
                            ),
                        },
                    ],
                    response_format={
                        "type": "json_object",
                        "schema": self._SCHEMA,
                    },
                    temperature=0.0,
                    max_tokens=self._max_tokens,
                    stream=False,
                ),
            )

        content = response["choices"][0]["message"]["content"]

        if not isinstance(content, str):
            raise TypeError(
                "Information extractor returned no textual content."
            )

        extracted: dict[str, Any] = json.loads(content)

        retval = []            
        for field_name, value in extracted.items():
            information = self._build_information(field_name, value)
            if information is not None:
                retval.append(information)
        
        return retval

    def warm_up(self) -> None:
        """Run one representative extraction before guest traffic starts."""

        self.extract(Message(content="I would like to check availability."))

    def _build_information(
        self,
        field_name: str,
        value: Any,
    ) -> Information | None:
        try:
            information_field = self._FIELD_MAP[field_name]

            if information_field in {
                InformationField.CHECK_IN,
                InformationField.CHECK_OUT,
            }:
                value = date.fromisoformat(value)
        
            information = Information(
                information_field=information_field,
                content=value,
            )
            
            return information
        
        except (ValueError, TypeError, KeyError) as error:
            LOG_MSG.debug(f"Invalid Information: {field_name}={value!r} ({error})")
            return None
