"""Implementation of the extract_information conversation graph node."""

from __future__ import annotations

import re

from .context import ConversationNodeContext
from .support import (
    BookingSelection,
    ConversationState,
    Information,
    InformationField,
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


def extract_information(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Extract information on every turn, independently of intent."""

    translated_message = _required_message(state, "translated_message")

    booking_selection = BookingSelection.from_wire(translated_message.content)
    if booking_selection is not None:
        return {
            "extracted_information": _booking_selection_information(booking_selection)
        }

    message = translated_message
    original_message = state.get("parsed_message")
    if (
        state.get("expected_interaction") is not None
        and isinstance(original_message, Message)
    ):
        message = original_message

    try:
        extracted = context.information_extractor.extract(message=message)
        valid_information = _valid_extracted_information(extracted)
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Information extraction failed", error)
        valid_information = []

    requested_fields = _open_requested_fields(state)

    if (
        not requested_fields
        or not isinstance(original_message, Message)
        or original_message.content == message.content
    ):
        return {"extracted_information": valid_information}

    literal_emails = _literal_emails(original_message.content)
    valid_information = _apply_original_email_authority(
        valid_information,
        requested_fields=requested_fields,
        literal_emails=literal_emails,
    )
    missing_fields = _missing_requested_fields(
        requested_fields,
        valid_information,
    )

    if not missing_fields:
        return {"extracted_information": valid_information}

    try:
        original_extracted = context.information_extractor.extract(
            message=original_message
        )
        original_information = _valid_extracted_information(original_extracted)
    except Exception as error:  # noqa: BLE001
        _safe_log_exception("Original-message information extraction failed", error)
        return {"extracted_information": valid_information}

    accepted_fields = _candidate_fields(missing_fields)
    original_information = [
        information
        for information in original_information
        if information.information_field in accepted_fields
        and _is_authoritative_email(information, literal_emails)
    ]

    valid_information = _merge_information(
        valid_information,
        original_information,
    )
    return {"extracted_information": valid_information}


def _literal_emails(content: str) -> dict[str, str]:
    return {
        match.group(0).casefold(): match.group(0)
        for match in _EMAIL_LITERAL_PATTERN.finditer(content)
    }


def _apply_original_email_authority(
    extracted: list[Information],
    *,
    requested_fields: frozenset[InformationField],
    literal_emails: dict[str, str],
) -> list[Information]:
    if InformationField.EMAIL not in requested_fields:
        return extracted

    by_field = {
        information.information_field: information for information in extracted
    }
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
    extracted_fields = {
        information.information_field for information in extracted
    }

    return frozenset(
        field
        for field in requested_fields
        if not _candidate_fields(frozenset({field})) & extracted_fields
    )


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
    by_field = {information.information_field: information for information in primary}
    for information in fallback:
        by_field[information.information_field] = information
    return list(by_field.values())


__all__ = ["extract_information"]
