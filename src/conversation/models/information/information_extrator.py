import json
from datetime import date
from pathlib import Path
from typing import Any

from llama_cpp import Llama

from conversation.entities.information import Information
from conversation.models.information.interface import InformationExtractorInterface
from conversation.value_object.information_fields import InformationField
from conversation.entities.message import Message

from conversation.models.information.information_extraction_schema import get_information_extraction_schema, get_field_map
from conversation.models.information.information_extraction_system_prompt import get_system_prompt

from configuration.application import ApplicationSettings


class InformationExtractor(InformationExtractorInterface):

    _SCHEMA = get_information_extraction_schema()
    _FIELD_MAP = get_field_map()
    _SYSTEM_PROMPT = get_system_prompt()

    def __init__(self) -> None:
        self._model = Llama(
            model_path=str(ApplicationSettings.get_settings().information_extraction_model),
            n_ctx=2048,
            max_tokens=128,
            n_gpu_layers=0,
            verbose=False,
        )
        print(f"{type(self).__name__} loaded")

    def extract(self, message: Message) -> list[Information]:
        """Try to extract information fields from given user message."""
        confirmation = self._extract_confirmation(message.content)

        if confirmation is not None:
            print(f"(info extractor) confirmation info extracted:{confirmation}")
            return [
                Information(
                    information_field=InformationField.CONFIRMATION,
                    content=confirmation,
                )
            ]
        
        response = self._model.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": self._SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Current date: {date.today().isoformat()}\n\n"
                        f"User message:\n{message.content}"
                    ),
                },
            ],
            response_format={
                "type": "json_object",
                "schema": self._SCHEMA,
            },
            temperature=0.0,
            max_tokens=256,
        )

        content = response["choices"][0]["message"]["content"]

        if not isinstance(content, str):
            raise RuntimeError(
                "Information extractor returned no textual content."
            )

        extracted: dict[str, Any] = json.loads(content)

        retval = []            
        for field_name, value in extracted.items():
            information = self._build_information(field_name, value)
            if information is not None:
                retval.append(information)
        
        return retval

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
            print(
                f"Invalid Information: "
                f"{field_name}={value!r} ({error})"
    )
            return None
    

    def _extract_confirmation(self, content: str) -> str | None:
        normalized = " ".join(
            content.casefold().strip().split()
        ).strip(".,!?")

        affirmative = {
            "yes",
            "yes please",
            "sure",
            "okay",
            "ok",
            "go ahead",
            "sounds good",
        }

        negative = {
            "no",
            "no thanks",
            "no thank you",
            "never mind",
            "decline",
            "stop",
        }

        if normalized in affirmative:
            return "yes"

        if normalized in negative:
            return "no"

        return None