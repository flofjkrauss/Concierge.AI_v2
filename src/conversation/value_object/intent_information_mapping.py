"""Map relevant and required information fields to conversation intents."""

from dataclasses import dataclass
from typing import ClassVar

from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


@dataclass(slots=True, frozen=True)
class IntentInformationMapper:
    """Distinguish fields an intent can use from fields it must collect."""

    _RELEVANT_FIELDS: ClassVar[dict[Intent, tuple[InformationField, ...]]] = {
        Intent.AVAILABILITY_CHECK: (
            InformationField.CHECK_IN,
            InformationField.CHECK_OUT,
            InformationField.GUEST_COUNT,
            InformationField.ACCESSIBLE,
        ),
        Intent.BOOKING_CHECK: (
            InformationField.LAST_NAME,
            InformationField.EMAIL,
            InformationField.CHECK_IN,
        ),
        Intent.BOOKING_CANCELLATION: (
            InformationField.LAST_NAME,
            InformationField.EMAIL,
            InformationField.CHECK_IN,
        ),
        Intent.BOOKING_REQUEST: (
            InformationField.CHECK_IN,
            InformationField.CHECK_OUT,
            InformationField.GUEST_COUNT,
            InformationField.ACCESSIBLE,
            InformationField.BREAKFAST,
            InformationField.FIRST_NAME,
            InformationField.LAST_NAME,
            InformationField.EMAIL,
            InformationField.ROOM_CATEGORY,
            InformationField.PHONE,
            InformationField.PREFERRED_LANG,
        ),
        Intent.INFORMATION_REQUEST: (InformationField.INFORMATION_TOPIC,),
        Intent.CONVERSATION_INITIATION: (),
        Intent.UNKNOWN: (),
    }

    _OPTIONAL_FIELDS: ClassVar[dict[Intent, frozenset[InformationField]]] = {
        Intent.BOOKING_REQUEST: frozenset({InformationField.PHONE}),
    }

    @classmethod
    def determine_fields(cls, intent: Intent) -> list[InformationField]:
        """Return all fields that can contribute to ``intent``."""

        return list(cls._RELEVANT_FIELDS[intent])

    @classmethod
    def determine_required_fields(
        cls,
        intent: Intent,
    ) -> list[InformationField]:
        """Return only fields that must be present before execution."""

        optional_fields = cls._OPTIONAL_FIELDS.get(intent, frozenset())
        required_fields: list[InformationField] = []
        for field in cls._RELEVANT_FIELDS[intent]:
            if field not in optional_fields:
                required_fields.append(field)

        return required_fields
