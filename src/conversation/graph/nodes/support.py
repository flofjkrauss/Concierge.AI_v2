"""Shared validation and state helpers for conversation graph nodes."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal, Protocol, assert_never

from configuration.application import ApplicationSettings
from conversation.entities.information import Information
from conversation.entities.interaction_response import (
    BookingResponseObject,
    ErrorResponse,
    InteractionResponse,
)
from conversation.entities.message import Message
from conversation.graph.state import (
    ConfirmationOutcome,
    ConversationMessage,
    ConversationState,
    DomainOperation,
    ExpectedInteraction,
    ExpectedInteractionKind,
    MessageRole,
)
from conversation.models.information.interface import InformationExtractorInterface
from conversation.models.intent.interface import IntentionDetectorInterface
from conversation.models.translation.interface import TranslatorInterface
from conversation.user_interaction import UserInteraction
from conversation.value_object.action import Action
from conversation.value_object.booking_selection import BookingSelection
from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent
from conversation.value_object.intent_information_mapping import (
    IntentInformationMapper,
)
from database.interface import DatabaseInterface
from domain.entities.booking import Booking
from domain.entities.booking_request import BookingRequest
from domain.entities.customer import Customer
from domain.entities.room import Room
from domain.services.calculate_price import calculate_price
from domain.services.cancel_booking import cancel_booking_by_name
from domain.services.confirm_booking import confirm_booking
from domain.services.create_customer import create_customer
from domain.services.find_matching_rooms import MatchResponse, find_matching_rooms
from domain.services.get_booking import get_booking_by_name
from domain.services.get_information import get_information
from domain.value_objects.booking_status import BookingStatus
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.money import Money
from domain.value_objects.room_category import RoomCategory
from domain.value_objects.stay_period import StayPeriod
from observability.log_messages import LOG_MSG
from observability.utils.to_json import to_jsonable

__all__ = [
    "LOG_MSG",
    "Action",
    "ApplicationSettings",
    "BookingResponseObject",
    "BookingSelection",
    "BookingStatus",
    "ConfirmationOutcome",
    "ConversationMessage",
    "ConversationState",
    "DatabaseInterface",
    "DomainOperation",
    "ExpectedInteraction",
    "ExpectedInteractionKind",
    "Information",
    "InformationExtractorInterface",
    "InformationField",
    "InformationTopic",
    "Intent",
    "IntentInformationMapper",
    "IntentionDetectorInterface",
    "InteractionResponse",
    "Mapping",
    "MatchResponse",
    "Message",
    "MessageRole",
    "Protocol",
    "TranslatorInterface",
    "assert_never",
    "calculate_price",
    "cancel_booking_by_name",
    "confirm_booking",
    "find_matching_rooms",
    "get_booking_by_name",
    "get_information",
    "replace",
    "to_jsonable",
]

StateUpdate = dict[str, object]

_MAX_CHECKPOINT_STRING_LENGTH = 16_384

_MAX_EXTRACTED_INFORMATION_ITEMS = len(InformationField)

_MAX_DOMAIN_ROOMS = 1_000

_DATA_INTENTS = frozenset(
    {
        Intent.AVAILABILITY_CHECK,
        Intent.BOOKING_CHECK,
        Intent.BOOKING_REQUEST,
        Intent.BOOKING_CANCELLATION,
        Intent.INFORMATION_REQUEST,
    }
)

_BOOKING_IDENTITY_FIELDS = (
    InformationField.FIRST_NAME,
    InformationField.LAST_NAME,
    InformationField.EMAIL,
)

_SESSION_IDENTITY_FIELDS = frozenset(_BOOKING_IDENTITY_FIELDS)

_PERSISTENT_INFORMATION_FIELDS = frozenset(
    {
        InformationField.PREFERRED_LANG,
        *_SESSION_IDENTITY_FIELDS,
    }
)

_REQUEST_INFORMATION_FIELDS = frozenset(
    field
    for intent in _DATA_INTENTS
    for field in IntentInformationMapper.determine_fields(intent)
    if field not in _PERSISTENT_INFORMATION_FIELDS
)

_BOOKING_FLOW_INTENTS = frozenset(
    {
        Intent.AVAILABILITY_CHECK,
        Intent.BOOKING_REQUEST,
    }
)

_BOOKING_REQUEST_CLEANUP_FIELDS = frozenset(
    set(IntentInformationMapper.determine_fields(Intent.BOOKING_REQUEST))
    - _PERSISTENT_INFORMATION_FIELDS
    - {InformationField.CHECK_IN}
)

_UNSUPPORTED_INFORMATION_RESPONSE = (
    "I don't have information about that hotel service. "
    "Is there anything else I can help with?"
)


def _safe_error_response(
    user_interaction: UserInteraction,
    *,
    reason: str,
    session_active: bool = True,
) -> ErrorResponse:
    """Return an error response even if a custom UI component fails."""

    try:
        response = user_interaction.send_error_msg(
            reason=reason,
            session_active=session_active,
        )
        if isinstance(response, ErrorResponse):
            return response
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Error response construction failed", error)

    return ErrorResponse(
        text="Something went terribly wrong!",
        session_active=session_active,
        reason=reason,
    )


def _safe_log_exception(message: str, error: Exception) -> None:
    """Record a boundary failure without allowing logging to break the turn."""

    try:
        LOG_MSG.error(f"{message} ({type(error).__name__})")
    except Exception:  # noqa: BLE001, S110
        pass


def _safe_log_warning(message: str) -> None:
    """Record an invalid component result without affecting the workflow."""

    try:
        LOG_MSG.warning(message)
    except Exception:  # noqa: BLE001, S110
        pass


def _valid_language_or_default(value: object, default: str) -> str:
    """Accept a bounded non-empty language identifier or use the default."""

    if not isinstance(value, str):
        _safe_log_warning("Language detector returned a non-string value")
        return default

    language = value.strip()
    if not language or len(language) > 32 or not _is_checkpoint_safe_string(language):
        _safe_log_warning("Language detector returned an invalid identifier")
        return default
    return language


def _is_usable_message(value: object) -> bool:
    """Return whether a translator result can safely enter graph state."""

    if not isinstance(value, Message):
        return False

    try:
        return (
            _is_checkpoint_safe_string(value.content)
            and bool(value.content.strip())
            and _is_checkpoint_safe_string(value.original_content)
            and _is_checkpoint_safe_string(value.language)
            and _is_checkpoint_safe_string(value.message_id)
            and bool(value.message_id.strip())
            and isinstance(value.created_at, datetime)
            and value.created_at.tzinfo is not None
            and value.created_at.utcoffset() is not None
        )
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Translator message validation failed", error)
        return False


def _valid_extracted_information(value: object) -> list[Information]:
    """Filter extractor output to valid, checkpoint-safe information values."""

    if not isinstance(value, (list, tuple)):
        _safe_log_warning("Information extractor returned a non-list value")
        return []

    if len(value) > _MAX_EXTRACTED_INFORMATION_ITEMS:
        _safe_log_warning("Information extractor returned too many items")

    valid: list[Information] = []
    for item in value[:_MAX_EXTRACTED_INFORMATION_ITEMS]:
        if _is_valid_information(item):
            valid.append(item)
        else:
            _safe_log_warning("Information extractor returned an invalid item")
    return _deduplicate_information(valid)


def _is_valid_information(value: object) -> bool:
    """Validate one information object without trusting component behavior."""

    if not isinstance(value, Information):
        return False
    try:
        return (
            isinstance(value.information_id, str)
            and bool(value.information_id.strip())
            and isinstance(value.created_at, datetime)
            and value.created_at.tzinfo is not None
            and value.created_at.utcoffset() is not None
            and value.is_valid()
            and (
                not isinstance(value.content, str)
                or _is_checkpoint_safe_string(value.content)
            )
        )
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Information validation failed", error)
        return False


def _is_valid_domain_result(
    operation: DomainOperation,
    result: object,
) -> bool:
    """Keep arbitrary adapter objects out of checkpointed graph state."""

    if operation in {
        DomainOperation.FIND_AVAILABILITY,
        DomainOperation.CHECK_BOOKING_AVAILABILITY,
    }:
        return _is_valid_match_response(result)
    if operation in {
        DomainOperation.PREVIEW_BOOKING,
        DomainOperation.CREATE_BOOKING,
    }:
        return _is_valid_booking_response(result) or _is_valid_match_response(result)
    if operation in {
        DomainOperation.GET_BOOKING,
        DomainOperation.CANCEL_BOOKING,
    }:
        return result is None or _is_valid_booking_response(result)
    if operation == DomainOperation.GET_INFORMATION:
        return _is_checkpoint_safe_string(result)
    return False


def _is_valid_match_response(value: object) -> bool:
    if not isinstance(value, MatchResponse):
        return False
    if value.request is not None and not _is_valid_booking_request(value.request):
        return False
    return (
        isinstance(value.rooms, list)
        and len(value.rooms) <= _MAX_DOMAIN_ROOMS
        and all(_is_valid_room(room) for room in value.rooms)
    )


def _is_valid_booking_response(value: object) -> bool:
    if not isinstance(value, BookingResponseObject):
        return False
    return (
        isinstance(value.status, BookingStatus)
        and _is_checkpoint_safe_string(value.room_category)
        and bool(value.room_category.strip())
        and isinstance(value.guest_count, int)
        and not isinstance(value.guest_count, bool)
        and value.guest_count > 0
        and isinstance(value.check_in, date)
        and isinstance(value.check_out, date)
        and value.check_out > value.check_in
        and _is_valid_money(value.total_prize)
        and isinstance(value.accessible, bool)
        and isinstance(value.breakfast, bool)
        and _is_checkpoint_safe_string(value.first_name)
        and _is_checkpoint_safe_string(value.last_name)
        and _is_checkpoint_safe_string(value.email)
        and (value.phone is None or _is_checkpoint_safe_string(value.phone))
    )


def _is_valid_booking_request(value: object) -> bool:
    if not isinstance(value, BookingRequest):
        return False
    return (
        _is_checkpoint_safe_string(value.request_id)
        and bool(value.request_id.strip())
        and isinstance(value.stay_period, StayPeriod)
        and isinstance(value.stay_period.check_in, date)
        and isinstance(value.stay_period.check_out, date)
        and value.stay_period.check_out > value.stay_period.check_in
        and isinstance(value.guest_count, int)
        and not isinstance(value.guest_count, bool)
        and value.guest_count > 0
        and isinstance(value.breakfast_included, bool)
        and isinstance(value.accessible_requested, bool)
    )


def _is_valid_room(value: object) -> bool:
    if not isinstance(value, Room):
        return False
    return (
        _is_checkpoint_safe_string(value.room_id)
        and bool(value.room_id.strip())
        and _is_checkpoint_safe_string(value.room_number)
        and bool(value.room_number.strip())
        and isinstance(value.floor, int)
        and not isinstance(value.floor, bool)
        and isinstance(value.category, RoomCategory)
        and isinstance(value.max_occupancy, int)
        and not isinstance(value.max_occupancy, bool)
        and value.max_occupancy > 0
        and _is_valid_money(value.price_per_night)
        and isinstance(value.is_accessible, bool)
        and isinstance(value.is_bookable, bool)
    )


def _is_valid_money(value: object) -> bool:
    return (
        isinstance(value, Money)
        and isinstance(value.amount, Decimal)
        and value.amount >= Decimal(0)
        and _is_checkpoint_safe_string(value.currency)
        and len(value.currency) == 3
    )


def _is_checkpoint_safe_string(value: object) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) > _MAX_CHECKPOINT_STRING_LENGTH:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _is_valid_interaction_response(value: object) -> bool:
    return (
        isinstance(value, InteractionResponse)
        and isinstance(value.session_active, bool)
        and _is_checkpoint_safe_string(value.text)
    )


def _required_message(
    state: ConversationState,
    key: Literal["parsed_message", "translated_message"],
) -> Message:
    value = state.get(key)

    if not isinstance(value, Message):
        raise TypeError(f"State field {key} must contain a Message")

    return value


def _confirmation_decision(content: str) -> bool | None:
    normalized = " ".join(content.casefold().strip().split()).strip(".,!?")

    affirmative = {
        "yes",
        "yes please",
        "confirm",
        "confirmed",
        "proceed",
    }

    negative = {
        "no",
        "no thanks",
        "decline",
        "stop",
    }

    if normalized in affirmative:
        return True

    if normalized in negative:
        return False

    first_word = normalized.partition(" ")[0].rstrip(",:;")

    if first_word in {"yes", "confirm", "confirmed"}:
        return True

    if first_word in {"no", "decline", "stop"}:
        return False

    return None


def _filter_context_dependent_information(
    extracted: list[Information],
    content: str,
) -> tuple[list[Information], bool]:
    """Reject model choices that are not supported by the current message."""

    supported_topic = _mentioned_information_topic(content)
    supported_room_category = _mentioned_room_category(content)
    date_is_mentioned = _message_mentions_date(content)
    filtered: list[Information] = []
    rejected_information_topic = False

    for information in extracted:
        if (
            information.information_field
            in {InformationField.CHECK_IN, InformationField.CHECK_OUT}
            and not date_is_mentioned
        ):
            continue

        if information.information_field == InformationField.INFORMATION_TOPIC:
            if supported_topic is None:
                rejected_information_topic = True
                continue
            filtered.append(replace(information, content=supported_topic))
            continue

        if information.information_field == InformationField.ROOM_CATEGORY:
            if supported_room_category is None:
                continue
            filtered.append(replace(information, content=supported_room_category))
            continue

        filtered.append(information)

    return _deduplicate_information(filtered), rejected_information_topic


def _mentioned_information_topic(content: str) -> InformationTopic | None:
    normalized = " ".join(content.casefold().strip().split())
    aliases: tuple[tuple[InformationTopic, tuple[str, ...]], ...] = (
        (InformationTopic.EARLY_CHECK_IN, ("early check-in", "early check in")),
        (InformationTopic.LATE_CHECK_OUT, ("late check-out", "late check out")),
        (InformationTopic.ROOM_SERVICE, ("room service", "in-room dining")),
        (InformationTopic.ROOM_CATEGORIES, ("room categories", "room types")),
        (InformationTopic.SERVICE_ANIMALS, ("service animal", "service dog")),
        (InformationTopic.EV_CHARGING, ("ev charging", "electric vehicle")),
        (InformationTopic.FAMILY_SERVICES, ("family service", "cot", "high chair")),
        (InformationTopic.LUGGAGE_STORAGE, ("luggage storage", "store luggage")),
        (
            InformationTopic.PAYMENT_METHODS,
            ("payment method", "pay with", "credit card"),
        ),
        (
            InformationTopic.CANCELLATION_POLICY,
            ("cancellation policy", "cancel policy"),
        ),
        (InformationTopic.PUBLIC_TRANSPORT, ("public transport", "bus stop", "train")),
        (InformationTopic.AIRPORT_TRANSFER, ("airport transfer", "airport shuttle")),
        (
            InformationTopic.LOCAL_ATTRACTIONS,
            ("local attraction", "nearby attraction", "sightseeing"),
        ),
        (InformationTopic.FRONT_DESK, ("front desk", "reception")),
        (InformationTopic.ACCESSIBILITY, ("accessibility", "accessible", "wheelchair")),
        (InformationTopic.CHECK_OUT, ("check-out", "check out", "departure time")),
        (InformationTopic.CHECK_IN, ("check-in", "check in", "arrival time")),
        (InformationTopic.WIFI, ("wi-fi", "wifi", "internet")),
        (InformationTopic.BREAKFAST, ("breakfast",)),
        (InformationTopic.PETS, ("pet", "dog", "cat")),
        (InformationTopic.PARKING, ("parking", "park my car")),
        (InformationTopic.LOCATION, ("location", "address", "located")),
        (InformationTopic.RESTAURANT, ("restaurant", "dinner")),
        (InformationTopic.BAR, ("hotel bar", " bar", "bar ")),
        (InformationTopic.SMOKING, ("smoking", "smoke")),
        (InformationTopic.HOUSEKEEPING, ("housekeeping", "cleaning")),
        (InformationTopic.LAUNDRY, ("laundry",)),
        (InformationTopic.CONTACT, ("contact", "phone number", "email address")),
    )

    for topic, topic_aliases in aliases:
        if any(alias in normalized for alias in topic_aliases):
            return topic
    return None


def _mentioned_room_category(content: str) -> RoomCategory | None:
    normalized = " ".join(content.casefold().strip().split())

    for category in RoomCategory:
        if re.search(
            rf"\b{re.escape(category.value)}(?:\s+room)?\b",
            normalized,
        ):
            return category
    return None


def _message_mentions_date(content: str) -> bool:
    """Return whether the current message contains an explicit date anchor."""

    normalized = " ".join(content.casefold().strip().split())

    if not normalized:
        return False

    date_words = (
        "today",
        "tomorrow",
        "tonight",
        "yesterday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "weekend",
    )

    if any(re.search(rf"\b{word}\b", normalized) for word in date_words):
        return True

    return any(
        re.search(pattern, normalized) is not None
        for pattern in (
            r"\b(?:next|this)\s+(?:week|month)\b",
            r"\b(?:in|after)\s+(?:a|an|one|two|three|\d+)\s+days?\b",
            r"\b(?:a|an|one|two|three|\d+)\s+days?\s+from\s+now\b",
            r"\b\d{4}-\d{1,2}-\d{1,2}\b",
            r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b",
            r"\b\d{1,2}(?:st|nd|rd|th)\b",
        )
    )


def _coerce_requested_boolean(
    extracted: list[Information],
    next_missing_field: InformationField | None,
) -> list[Information]:
    """Convert a generic yes/no extraction into the requested boolean field."""

    converted: list[Information] = []

    for information in extracted:
        if information.information_field != InformationField.CONFIRMATION:
            converted.append(information)
            continue

        if next_missing_field in {
            InformationField.BREAKFAST,
            InformationField.ACCESSIBLE,
        } and information.content in {"yes", "no"}:
            converted.append(
                Information(
                    information_field=next_missing_field,
                    content=information.content == "yes",
                )
            )

    return _deduplicate_information(converted)


def _coerce_requested_date(
    extracted: list[Information],
    next_missing_field: InformationField | None,
    content: str,
) -> list[Information]:
    """Assign an isolated extracted date to the date field being requested."""

    date_fields = {
        InformationField.CHECK_IN,
        InformationField.CHECK_OUT,
    }

    if next_missing_field not in date_fields:
        return extracted

    extracted_dates = [
        information
        for information in extracted
        if information.information_field in date_fields
    ]

    if not extracted_dates:
        return extracted

    if len(extracted_dates) > 1 and _looks_like_date_range(content):
        return extracted

    if len(extracted_dates) == 1:
        information = extracted_dates[0]
    else:
        information = _date_matching_explicit_weekday(
            extracted_dates,
            content,
        )
        if information is None:
            information = next(
                (
                    candidate
                    for candidate in extracted_dates
                    if candidate.information_field == next_missing_field
                ),
                extracted_dates[-1],
            )

    non_date_information = [
        item for item in extracted if item.information_field not in date_fields
    ]
    return _deduplicate_information(
        [
            *non_date_information,
            replace(information, information_field=next_missing_field),
        ]
    )


def _looks_like_date_range(content: str) -> bool:
    normalized = " ".join(content.casefold().strip().split())
    return any(
        re.search(pattern, normalized) is not None
        for pattern in (
            r"\bfrom\b.+\b(?:to|until|through)\b",
            r"\bbetween\b.+\band\b",
            r"\b\d+\s+nights?\s+from\b",
            r"\d[^\n]*\s[-–]\s*\d",
        )
    )


def _date_matching_explicit_weekday(
    extracted_dates: Iterable[Information],
    content: str,
) -> Information | None:
    normalized = content.casefold()
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    mentioned_weekday = next(
        (
            weekday
            for name, weekday in weekdays.items()
            if re.search(rf"\b{name}\b", normalized)
        ),
        None,
    )

    if mentioned_weekday is None:
        return None

    return next(
        (
            information
            for information in extracted_dates
            if (
                isinstance(information.content, date)
                and information.content.weekday() == mentioned_weekday
            )
        ),
        None,
    )


def _deduplicate_information(
    extracted: Iterable[Information],
) -> list[Information]:
    """Keep the last extracted value for each field in stable field order."""

    by_field: dict[InformationField, Information] = {}

    for information in extracted:
        by_field[information.information_field] = information

    return list(by_field.values())


def _plausible_information(
    extracted: list[Information],
    existing: Mapping[InformationField, Information],
) -> tuple[list[Information], set[InformationField]]:
    """Discard obviously invalid dates before storage or confirmation."""

    candidates = {
        information.information_field: information for information in extracted
    }
    invalid_fields: set[InformationField] = set()
    today = datetime.now(UTC).astimezone().date()

    for field in {
        InformationField.CHECK_IN,
        InformationField.CHECK_OUT,
    }:
        information = candidates.get(field)

        if information is None:
            continue

        if not isinstance(information.content, date) or information.content < today:
            invalid_fields.add(field)

    new_check_in = _candidate_date(
        candidates,
        InformationField.CHECK_IN,
        invalid_fields,
    )
    new_check_out = _candidate_date(
        candidates,
        InformationField.CHECK_OUT,
        invalid_fields,
    )
    effective_check_in = new_check_in or _stored_date(
        existing,
        InformationField.CHECK_IN,
    )
    effective_check_out = new_check_out or _stored_date(
        existing,
        InformationField.CHECK_OUT,
    )

    if (
        effective_check_in is not None
        and effective_check_out is not None
        and effective_check_out <= effective_check_in
    ):
        if new_check_in is not None:
            invalid_fields.add(InformationField.CHECK_IN)
        if new_check_out is not None:
            invalid_fields.add(InformationField.CHECK_OUT)

    return (
        [
            information
            for information in candidates.values()
            if information.information_field not in invalid_fields
        ],
        invalid_fields,
    )


def _candidate_date(
    candidates: Mapping[InformationField, Information],
    field: InformationField,
    invalid_fields: set[InformationField],
) -> date | None:
    if field in invalid_fields:
        return None

    information = candidates.get(field)

    if information is None or not isinstance(information.content, date):
        return None

    return information.content


def _stored_date(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> date | None:
    stored = information.get(field)

    if stored is None or not isinstance(stored.content, date):
        return None

    return stored.content


def _active_data_intent(
    state: ConversationState,
    extracted: Iterable[Information] = (),
) -> Intent | None:
    detected = state.get("detected_intent") or Intent.UNKNOWN

    if detected in _DATA_INTENTS:
        return detected

    current = state.get(
        "current_intent",
        Intent.CONVERSATION_INITIATION,
    )

    if current in _DATA_INTENTS:
        if not state.get("last_intent_fulfilled", False):
            return current

        relevant_fields = set(IntentInformationMapper.determine_fields(current))
        if any(
            information.information_field in relevant_fields
            for information in extracted
        ):
            return current

    return None


def _refines_fulfilled_intent(
    state: ConversationState,
    extracted: Iterable[Information],
) -> bool:
    if not state.get("last_intent_fulfilled", False):
        return False

    current = state.get("current_intent")
    detected = state.get("detected_intent") or Intent.UNKNOWN

    if current not in _DATA_INTENTS or detected not in {
        Intent.UNKNOWN,
        current,
    }:
        return False

    relevant_fields = set(IntentInformationMapper.determine_fields(current))
    return any(
        information.information_field in relevant_fields for information in extracted
    )


def _starts_new_data_scope(
    state: ConversationState,
    *,
    refining_fulfilled_intent: bool,
) -> bool:
    if state.get("expected_interaction") is not None:
        return False

    detected = state.get("detected_intent") or Intent.UNKNOWN
    current = state.get(
        "current_intent",
        Intent.CONVERSATION_INITIATION,
    )

    if detected not in _DATA_INTENTS:
        return False

    return detected != current or (
        state.get("last_intent_fulfilled", False) and not refining_fulfilled_intent
    )


def _invalid_date_to_report(
    invalid_fields: set[InformationField],
    *,
    requested_field: InformationField | None,
) -> InformationField | None:
    if requested_field in invalid_fields:
        return requested_field
    if InformationField.CHECK_OUT in invalid_fields:
        return InformationField.CHECK_OUT
    if InformationField.CHECK_IN in invalid_fields:
        return InformationField.CHECK_IN
    return None


def _information_change_data(
    existing: Mapping[InformationField, Information],
    pending: Mapping[InformationField, Information],
) -> dict[InformationField, tuple[object, object]]:
    replacements: dict[InformationField, tuple[object, object]] = {}

    for field, replacement in pending.items():
        current = existing.get(field)

        if current is None:
            continue

        replacements[field] = (current.content, replacement.content)

    return replacements


def _information_removals(
    fields: Iterable[InformationField],
) -> dict[InformationField, None]:
    return dict.fromkeys(fields)


def _fields_for_data_request(
    state: ConversationState,
    requested_field: InformationField,
) -> list[InformationField]:
    """Group missing booking identity fields on their first request."""

    if state.get("current_intent") != Intent.BOOKING_REQUEST:
        return [requested_field]

    if requested_field not in _BOOKING_IDENTITY_FIELDS:
        return [requested_field]

    missing_fields = set(state.get("missing_fields", []))
    if all(field in missing_fields for field in _BOOKING_IDENTITY_FIELDS):
        return list(_BOOKING_IDENTITY_FIELDS)

    name_fields = _BOOKING_IDENTITY_FIELDS[:2]
    if all(field in missing_fields for field in name_fields):
        return list(name_fields)

    return [requested_field]


def _booking_selection_information(
    selection: BookingSelection,
) -> list[Information]:
    """Convert one validated client selection into authoritative fields."""

    return [
        Information(InformationField.CHECK_IN, selection.check_in),
        Information(InformationField.CHECK_OUT, selection.check_out),
        Information(InformationField.GUEST_COUNT, selection.guest_count),
        Information(InformationField.ACCESSIBLE, selection.accessible),
        Information(
            InformationField.ROOM_CATEGORY,
            selection.room_category.value,
        ),
    ]


def _booking_request_tuple_from_information(
    information: Mapping[InformationField, Information],
) -> tuple[date, date, int, bool, bool | None]:
    check_in = _required_date(
        information,
        InformationField.CHECK_IN,
    )
    check_out = _required_date(
        information,
        InformationField.CHECK_OUT,
    )
    guest_count = _required_int(
        information,
        InformationField.GUEST_COUNT,
    )
    accessible = _required_bool(
        information,
        InformationField.ACCESSIBLE,
    )
    breakfast = _optional_bool(
        information,
        InformationField.BREAKFAST,
        default=False,
    )

    return (
        check_in,
        check_out,
        guest_count,
        accessible,
        breakfast,
    )


def _early_availability_tuple_from_information(
    information: Mapping[InformationField, Information],
) -> tuple[date, date, int, bool, bool]:
    guest_information = information.get(InformationField.GUEST_COUNT)
    guest_count = (
        _required_int(information, InformationField.GUEST_COUNT)
        if guest_information is not None
        else 1
    )

    return (
        _required_date(information, InformationField.CHECK_IN),
        _required_date(information, InformationField.CHECK_OUT),
        guest_count,
        _optional_bool(
            information,
            InformationField.ACCESSIBLE,
            default=False,
        ),
        _optional_bool(
            information,
            InformationField.BREAKFAST,
            default=False,
        ),
    )


def _booking_availability_signature(
    information: Mapping[InformationField, Information],
) -> tuple[str, str, int | None, bool | None, str | None] | None:
    try:
        check_in = _required_date(information, InformationField.CHECK_IN)
        check_out = _required_date(information, InformationField.CHECK_OUT)
        guest_information = information.get(InformationField.GUEST_COUNT)
        guest_count = (
            _required_int(information, InformationField.GUEST_COUNT)
            if guest_information is not None
            else None
        )
        accessible_information = information.get(InformationField.ACCESSIBLE)
        accessible = (
            _required_bool(information, InformationField.ACCESSIBLE)
            if accessible_information is not None
            else None
        )
        category_information = information.get(InformationField.ROOM_CATEGORY)
        category = (
            _required_string(information, InformationField.ROOM_CATEGORY)
            if category_information is not None
            else None
        )
    except (KeyError, TypeError, ValueError):
        return None

    return (
        check_in.isoformat(),
        check_out.isoformat(),
        guest_count,
        accessible,
        category,
    )


def _create_customer_from_information(
    information: Mapping[InformationField, Information],
    database: DatabaseInterface,
) -> Customer:
    first_name = _required_string(
        information,
        InformationField.FIRST_NAME,
    )
    last_name = _required_string(
        information,
        InformationField.LAST_NAME,
    )
    email = _required_string(
        information,
        InformationField.EMAIL,
    )
    preferred_language = _required_string(
        information,
        InformationField.PREFERRED_LANG,
    )
    phone = _optional_string(
        information,
        InformationField.PHONE,
        default="0",
    )

    customer = create_customer(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        preferred_language=preferred_language,
        database=database,
    )

    if not isinstance(customer, Customer):
        raise TypeError("error in _create_customer_from_information")

    return customer


def _build_booking_response_data(
    booking: Booking | None,
    database: DatabaseInterface,
) -> BookingResponseObject | None:
    if booking is None:
        return None

    customer = database.get_customer(booking.customer_id)
    room = database.get_room(booking.room_id)

    if customer is None:
        raise RuntimeError(f"Customer not found for booking: {booking.booking_id}")

    if room is None:
        raise RuntimeError(f"Room not found for booking: {booking.booking_id}")

    return BookingResponseObject(
        status=booking.status,
        room_category=room.category,
        guest_count=booking.guest_count,
        check_in=booking.stay_period.check_in,
        check_out=booking.stay_period.check_out,
        total_prize=booking.total_price,
        accessible=booking.accessible_requested,
        breakfast=booking.breakfast_included,
        first_name=customer.first_name,
        last_name=customer.last_name,
        email=customer.email,
        phone=customer.phone,
    )


def _required_content(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> str | bool | int | date:
    try:
        return information[field].content

    except KeyError as error:
        raise KeyError(f"Missing required information: {field.value}") from error


def _required_string(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> str:
    value = _required_content(
        information,
        field,
    )

    if not isinstance(value, str):
        raise TypeError(f"{field.value} must be a string")

    return value


def _required_bool(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> bool:
    value = _required_content(
        information,
        field,
    )

    if not isinstance(value, bool):
        raise TypeError(f"{field.value} must be a boolean")

    return value


def _optional_bool(
    information: Mapping[InformationField, Information],
    field: InformationField,
    *,
    default: bool,
) -> bool:
    value = information.get(field)

    if value is None:
        return default

    if not isinstance(value.content, bool):
        raise TypeError(f"{field.value} must be a boolean")

    return value.content


def _optional_string(
    information: Mapping[InformationField, Information],
    field: InformationField,
    *,
    default: str,
) -> str:
    value = information.get(field)

    if value is None:
        return default

    if not isinstance(value.content, str):
        raise TypeError(f"{field.value} must be a string")

    return value.content


def _required_int(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> int:
    value = _required_content(
        information,
        field,
    )

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field.value} must be an integer")

    return value


def _required_date(
    information: Mapping[InformationField, Information],
    field: InformationField,
) -> date:
    value = _required_content(
        information,
        field,
    )

    if not isinstance(value, date):
        raise TypeError(f"{field.value} must be a date")

    return value
