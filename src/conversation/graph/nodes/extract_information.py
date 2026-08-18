"""Implementation of the extract_information conversation graph node."""

from __future__ import annotations

import re
from datetime import date

from .context import ConversationNodeContext
from .support import (
    BookingSelection,
    ConversationState,
    Information,
    InformationField,
    InformationTopicSelection,
    Message,
    StateUpdate,
    _booking_selection_information,
    _open_requested_fields,
    _required_message,
    _safe_log_exception,
    _valid_extracted_information,
)

_EMAIL_LITERAL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"(?![A-Za-z0-9-])"
)

_DATE_FIELDS = frozenset(
    {
        InformationField.CHECK_IN,
        InformationField.CHECK_OUT,
    }
)

_BOOLEAN_FIELDS = frozenset(
    {
        InformationField.BREAKFAST,
        InformationField.ACCESSIBLE,
    }
)

_INTEGER_FIELDS = frozenset({InformationField.GUEST_COUNT})

_NUMERIC_DATE_PATTERNS = (
    re.compile(r"(?P<year>\d{4})\s*-\s*(?P<month>\d{1,2})\s*-\s*(?P<day>\d{1,2})"),
    re.compile(
        r"(?P<day>\d{1,2})\s*[./]\s*(?P<month>\d{1,2})\s*[./]\s*"
        r"(?P<year>\d{4})"
    ),
)


def extract_information(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Extract information on every turn, independently of intent."""

    translated_message = _required_message(state, "translated_message")

    information_selection = InformationTopicSelection.from_wire(
        translated_message.content
    )
    if information_selection is not None:
        return {
            "extracted_information": [
                Information(
                    InformationField.INFORMATION_TOPIC,
                    information_selection.topic.value,
                )
            ]
        }

    booking_selection = BookingSelection.from_wire(translated_message.content)
    if booking_selection is not None:
        return {
            "extracted_information": _booking_selection_information(booking_selection)
        }

    original_message = state.get("parsed_message")
    requested_fields = _open_requested_fields(state)
    requested_field = state.get("next_missing_field")
    expected_field = None
    if requested_field in requested_fields:
        expected_field = requested_field

    model_expected_field = None
    if expected_field in _DATE_FIELDS:
        model_expected_field = expected_field

    # Exact numeric date replies bypass translation and model extraction.
    literal_date = _date_from_original_message(
        expected_field,
        original_message=original_message,
    )
    if literal_date is not None:
        return {
            "extracted_information": [literal_date],
            "original_message_extracted_fields": [literal_date.information_field],
        }

    original_available = isinstance(original_message, Message)
    use_original_first = original_available and (
        expected_field is not None or state.get("expected_interaction") is not None
    )
    message = translated_message
    if use_original_first:
        message = original_message

    try:
        extracted = context.information_extractor.extract(
            message=message,
            expected_field=model_expected_field,
        )
        valid_information = _valid_extracted_information(extracted)
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Information extraction failed", error)
        valid_information = []

    discard_expected_field = None
    if use_original_first:
        discard_expected_field = expected_field

    valid_information, original_information_request = (
        _discard_expected_value_for_information_request(
            valid_information,
            expected_field=discard_expected_field,
        )
    )
    original_fields: set[InformationField] = set()
    if use_original_first:
        for information in valid_information:
            original_fields.add(information.information_field)

    if original_information_request:
        return _extraction_update(valid_information, original_fields)

    integer_information = _integer_from_original_message(
        state,
        original_message=original_message,
        extracted=valid_information,
        requested_fields=requested_fields,
    )
    if integer_information is not None:
        return {
            "extracted_information": [integer_information],
            "original_message_extracted_fields": [
                integer_information.information_field
            ],
        }

    if (
        not requested_fields
        or not original_available
        or original_message.content == translated_message.content
    ):
        return _extraction_update(valid_information, original_fields)

    literal_emails = _literal_emails(original_message.content)
    valid_information = _apply_original_email_authority(
        valid_information,
        requested_fields=requested_fields,
        literal_emails=literal_emails,
    )
    if InformationField.EMAIL in requested_fields:
        extracted_email = False
        for information in valid_information:
            if information.information_field == InformationField.EMAIL:
                extracted_email = True
                break
        if extracted_email:
            original_fields.add(InformationField.EMAIL)

    missing_fields = _missing_requested_fields(
        requested_fields,
        valid_information,
    )

    if not missing_fields:
        return _extraction_update(valid_information, original_fields)

    fallback_message = original_message
    if use_original_first:
        fallback_message = translated_message
    fallback_is_original = not use_original_first

    try:
        fallback_extracted = context.information_extractor.extract(
            message=fallback_message,
            expected_field=model_expected_field,
        )
        fallback_information = _valid_extracted_information(fallback_extracted)
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Fallback information extraction failed", error)
        return _extraction_update(valid_information, original_fields)

    accepted_fields = _candidate_fields(missing_fields)
    primary_fields: set[InformationField] = set()
    for information in valid_information:
        primary_fields.add(information.information_field)

    accepted_fallback_information: list[Information] = []
    for information in fallback_information:
        if (
            information.information_field in accepted_fields
            and information.information_field not in primary_fields
            and _is_authoritative_email(information, literal_emails)
        ):
            accepted_fallback_information.append(information)
    fallback_information = accepted_fallback_information

    valid_information = _merge_information(
        valid_information,
        fallback_information,
    )
    if fallback_is_original:
        for information in fallback_information:
            original_fields.add(information.information_field)
    return _extraction_update(valid_information, original_fields)


def _date_from_original_message(
    expected_field: InformationField | None,
    *,
    original_message: object,
) -> Information | None:
    """Parse an unambiguous numeric date answer without using either model."""

    if expected_field not in _DATE_FIELDS or not isinstance(original_message, Message):
        return None

    content = original_message.content.strip()
    match: re.Match[str] | None = None
    for pattern in _NUMERIC_DATE_PATTERNS:
        match = pattern.fullmatch(content)
        if match is not None:
            break
    if match is None:
        return None

    try:
        value: object = date(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
        )
    except ValueError:
        value = content

    return Information(expected_field, value)


def _extraction_update(
    extracted: list[Information],
    original_fields: set[InformationField],
) -> StateUpdate:
    update: StateUpdate = {"extracted_information": extracted}
    if original_fields:
        extracted_original_fields: list[InformationField] = []
        for information in extracted:
            if information.information_field in original_fields:
                extracted_original_fields.append(information.information_field)
        update["original_message_extracted_fields"] = extracted_original_fields
    return update


def _discard_expected_value_for_information_request(
    extracted: list[Information],
    *,
    expected_field: InformationField | None,
) -> tuple[list[Information], bool]:
    """Keep an information question from becoming a booking-field answer."""

    information_request = False
    for information in extracted:
        if information.information_field == InformationField.INFORMATION_TOPIC:
            information_request = True
            break

    if expected_field is None or not information_request:
        return extracted, False

    filtered_information: list[Information] = []
    for information in extracted:
        if information.information_field != expected_field:
            filtered_information.append(information)

    return filtered_information, True


def _integer_from_original_message(
    state: ConversationState,
    *,
    original_message: object,
    extracted: list[Information],
    requested_fields: frozenset[InformationField],
) -> Information | None:
    """Parse a bare integer only when extraction returned no information."""

    requested_field = state.get("next_missing_field")
    if (
        requested_field not in _INTEGER_FIELDS
        or requested_field not in requested_fields
        or not isinstance(original_message, Message)
    ):
        return None

    try:
        value = int(original_message.content)
        return Information(requested_field, value)
    except (TypeError, ValueError):
        return None


def _literal_emails(content: str) -> dict[str, str]:
    literal_emails: dict[str, str] = {}
    for match in _EMAIL_LITERAL_PATTERN.finditer(content):
        literal_email = match.group(0)
        literal_emails[literal_email.casefold()] = literal_email
    return literal_emails


def _apply_original_email_authority(
    extracted: list[Information],
    *,
    requested_fields: frozenset[InformationField],
    literal_emails: dict[str, str],
) -> list[Information]:
    if InformationField.EMAIL not in requested_fields:
        return extracted

    by_field: dict[InformationField, Information] = {}
    for information in extracted:
        by_field[information.information_field] = information
    translated_email = by_field.get(InformationField.EMAIL)

    if translated_email is not None and isinstance(translated_email.content, str):
        literal = literal_emails.get(translated_email.content.casefold())
        if literal is not None:
            by_field[InformationField.EMAIL] = Information(
                InformationField.EMAIL,
                literal,
            )
            return list(by_field.values())

    by_field.pop(InformationField.EMAIL, None)

    if len(literal_emails) == 1:
        literal = next(iter(literal_emails.values()))
        by_field[InformationField.EMAIL] = Information(
            InformationField.EMAIL,
            literal,
        )

    return list(by_field.values())


def _missing_requested_fields(
    requested_fields: frozenset[InformationField],
    extracted: list[Information],
) -> frozenset[InformationField]:
    extracted_fields: set[InformationField] = set()
    for information in extracted:
        extracted_fields.add(information.information_field)

    missing_fields: set[InformationField] = set()
    for field in requested_fields:
        candidate_fields = _candidate_fields(frozenset({field}))
        if not candidate_fields & extracted_fields:
            missing_fields.add(field)

    return frozenset(missing_fields)


def _candidate_fields(
    requested_fields: frozenset[InformationField],
) -> frozenset[InformationField]:
    candidates = set(requested_fields)

    if requested_fields & _DATE_FIELDS:
        candidates.update(_DATE_FIELDS)
    if requested_fields & _BOOLEAN_FIELDS:
        candidates.add(InformationField.CONFIRMATION)

    return frozenset(candidates)


def _is_authoritative_email(
    information: Information,
    literal_emails: dict[str, str],
) -> bool:
    if information.information_field != InformationField.EMAIL:
        return True
    return (
        isinstance(information.content, str)
        and information.content.casefold() in literal_emails
    )


def _merge_information(
    primary: list[Information],
    fallback: list[Information],
) -> list[Information]:
    by_field: dict[InformationField, Information] = {}
    for information in primary:
        by_field[information.information_field] = information
    for information in fallback:
        by_field[information.information_field] = information
    return list(by_field.values())


__all__ = ["extract_information"]
