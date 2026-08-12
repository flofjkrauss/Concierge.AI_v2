"""Coversation information entity."""
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import uuid4

from conversation.value_object.information_fields import InformationField
from utils.information_validator import INFORMATION_VALIDATORS


@dataclass(slots=True)
class Information:
    """information object"""    
    information_field: InformationField
    content: str | bool | int | date
    information_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.information_id.strip():
            raise ValueError("information_id must not be empty")

        if not isinstance(self.information_field, InformationField):
            raise TypeError(f"unregistered information field: {self.information_field}")

        if not self.is_valid():
            raise ValueError(f"the given value {self.content} is invalid for information field {self.information_field}")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

    def is_valid(self) -> bool:
        validator = INFORMATION_VALIDATORS.get(self.information_field)

        if validator is None:
            return False

        return validator(self.content)
