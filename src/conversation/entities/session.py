"""conversation entity."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from configuration.application import ApplicationSettings
from conversation.data_collector import DataCollector
from conversation.entities.message import Message
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent


@dataclass(slots=True)
class Session:
    """session object"""
    collector: DataCollector
    last_intent_fullfilled: bool = False
    language: str = ApplicationSettings.get_settings().domain_language
    missing_fields: list[InformationField] = field(default_factory=list)
    messages: dict[str, Message] = field(default_factory=dict)
    unknown_counter: int = 0
    current_intent: Intent = Intent.CONVERSATION_INITIATION
    
    session_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise ValueError("session_id must not be empty")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        if not isinstance(self.collector, DataCollector):
            raise TypeError("collector must be of Type DataCollector")

        if self.collector is None:
            raise ValueError("collector must be set")

        if self.current_intent == Intent.UNKNOWN:
            raise ValueError("sessions current intent must not be UNKNOWN")

        if self.current_intent == Intent.INFORMATION_REQUEST:
                    raise ValueError("sessions current intent must not be INFORMATION_REQUEST")


    def increase_unknown_counter(self) -> int:
        self.unknown_counter += 1
        return self.unknown_counter

    def reset_unknown_counter(self) -> int:
        self.unknown_counter = 0
        return self.unknown_counter

    def add_message(self, message: Message) -> None:
        self.messages[message.message_id] = message

    def reset(self, intent: Intent) -> None:
        self.last_intent_fullfilled = False
        self.current_intent = intent
        self.missing_fields.clear()