"""Implementation of the update_progress conversation graph node."""

from __future__ import annotations

from .context import ConversationNodeContext
from .support import (
    _DATA_INTENTS,
    _SESSION_IDENTITY_FIELDS,
    _UNSUPPORTED_INFORMATION_RESPONSE,
    Action,
    BookingSelection,
    ConversationState,
    ExpectedInteraction,
    ExpectedInteractionKind,
    Information,
    InformationField,
    Intent,
    IntentInformationMapper,
    Message,
    StateUpdate,
    _active_data_intent,
    _coerce_requested_boolean,
    _coerce_requested_date,
    _filter_context_dependent_information,
    _information_change_data,
    _invalid_date_to_report,
    _open_requested_fields,
    _plausible_information,
    _refines_fulfilled_intent,
    _safe_log_warning,
    _starts_new_data_scope,
)


def update_progress(
    context: ConversationNodeContext, state: ConversationState
) -> StateUpdate:
    """Validate extracted values and apply them or request replacement approval."""

    existing_information = state.get("collected_information", {})
    expected = state.get("expected_interaction")
    translated_message = state.get("translated_message")
    current_content = (
        translated_message.content if isinstance(translated_message, Message) else ""
    )
    requested_field = state.get("next_missing_field") if expected is None else None
    extracted = state.get("extracted_information", [])
    original_fields = set(state.get("original_message_extracted_fields", []))
    confirmation_information = (
        [
            information
            for information in extracted
            if information.information_field == InformationField.CONFIRMATION
        ]
        if expected is not None
        else []
    )
    translated_extracted = [
        information
        for information in extracted
        if information.information_field not in original_fields
    ]
    original_extracted = [
        information
        for information in extracted
        if information.information_field in original_fields
    ]
    if BookingSelection.from_wire(current_content) is None:
        translated_extracted = _coerce_requested_date(
            translated_extracted,
            requested_field,
            current_content,
        )
    translated_extracted = _coerce_requested_boolean(
        translated_extracted,
        requested_field,
    )
    translated_extracted, translated_topic_rejected = (
        _filter_context_dependent_information(
            translated_extracted,
            current_content,
        )
    )

    original_message = state.get("parsed_message")
    original_content = (
        original_message.content if isinstance(original_message, Message) else ""
    )
    original_validation_content = "\n".join(
        content for content in (current_content, original_content) if content
    )
    original_extracted = _coerce_requested_date(
        original_extracted,
        requested_field,
        original_validation_content,
    )
    original_extracted = _coerce_requested_boolean(
        original_extracted,
        requested_field,
    )
    original_extracted, original_topic_rejected = (
        _filter_context_dependent_information(
            original_extracted,
            original_validation_content,
        )
    )
    extracted = [*translated_extracted, *original_extracted]
    rejected_information_topic = (
        translated_topic_rejected or original_topic_rejected
    )
    requested_fields = _open_requested_fields(state)
    continues_requested_intent = any(
        information.information_field in requested_fields
        for information in extracted
    )
    information_change_pending = (
        expected is not None
        and expected.kind == ExpectedInteractionKind.INFORMATION_CHANGE_CONFIRMATION
    )
    operation_confirmation_pending = (
        expected is not None and not information_change_pending
    )

    if information_change_pending:
        active_intent = expected.intent
    elif continues_requested_intent:
        current_intent = state.get("current_intent")
        active_intent = (
            current_intent if current_intent in _DATA_INTENTS else None
        )
    else:
        active_intent = _active_data_intent(state, extracted)
    relevant_fields = (
        set(IntentInformationMapper.determine_fields(active_intent))
        if active_intent is not None
        else set()
    )

    if relevant_fields:
        extracted = [
            information
            for information in extracted
            if information.information_field
            in relevant_fields | _SESSION_IDENTITY_FIELDS
        ]

    refining_fulfilled_intent = _refines_fulfilled_intent(
        state,
        extracted,
    )
    starts_new_scope = (
        False
        if continues_requested_intent
        else _starts_new_data_scope(
            state,
            refining_fulfilled_intent=refining_fulfilled_intent,
        )
    )
    effective_existing = existing_information

    extracted, invalid_fields = _plausible_information(
        extracted,
        effective_existing,
    )
    invalid_date_field = _invalid_date_to_report(
        invalid_fields,
        requested_field=requested_field,
    )

    information_updates: dict[InformationField, Information | None] = {}
    pending_changes = (
        dict(state.get("pending_information_changes", {}))
        if information_change_pending
        else {}
    )
    changed_fields: set[InformationField] = set()

    for information in extracted:
        field = information.information_field
        existing = effective_existing.get(field)

        if existing is None:
            information_updates[field] = information
            changed_fields.add(field)
            continue

        if existing.content == information.content:
            continue

        if (
            operation_confirmation_pending
            or starts_new_scope
            or refining_fulfilled_intent
            or active_intent is None
        ):
            information_updates[field] = information
            changed_fields.add(field)
            continue

        pending_changes[field] = information

    if pending_changes.keys() & {
        InformationField.CHECK_IN,
        InformationField.CHECK_OUT,
    }:
        for date_field in {
            InformationField.CHECK_IN,
            InformationField.CHECK_OUT,
        }:
            related_date = information_updates.pop(date_field, None)
            if related_date is not None:
                pending_changes[date_field] = related_date
                changed_fields.discard(date_field)

    intent = state.get("detected_intent") or Intent.UNKNOWN
    unknown_counter = state.get("unknown_counter", 0)

    if (
        intent == Intent.UNKNOWN
        and not extracted
        and expected is None
        and invalid_date_field is None
        and not rejected_information_topic
    ):
        unknown_counter += 1
    else:
        unknown_counter = 0

    updates: StateUpdate = {
        "collected_information": information_updates,
        "extracted_information": [*extracted, *confirmation_information],
        "changed_fields": list(changed_fields),
        "unknown_counter": unknown_counter,
        "termination_requested": (unknown_counter > context.max_unknown_messages),
    }

    if invalid_date_field is not None:
        updates.update(
            {
                "action": Action.REPORT_INVALID_DATE,
                "domain_data": invalid_date_field,
                "current_intent": active_intent,
                "last_intent_fulfilled": False,
                "next_missing_field": invalid_date_field,
            }
        )
        if information_change_pending:
            updates["pending_information_changes"] = pending_changes
        return updates

    if rejected_information_topic and active_intent == Intent.INFORMATION_REQUEST:
        updates.update(
            {
                "action": Action.DISPLAY_INFO,
                "domain_data": _UNSUPPORTED_INFORMATION_RESPONSE,
                "current_intent": active_intent,
                "last_intent_fulfilled": True,
            }
        )

    if information_change_pending:
        updates["pending_information_changes"] = pending_changes
    elif pending_changes:
        if active_intent is None:
            _safe_log_warning("Pending information changes had no active data intent")
            updates["pending_information_changes"] = {}
            return updates

        pending_interaction = ExpectedInteraction(
            kind=ExpectedInteractionKind.INFORMATION_CHANGE_CONFIRMATION,
            intent=active_intent,
            operation=None,
        )
        updates.update(
            {
                "expected_interaction": pending_interaction,
                "pending_information_changes": pending_changes,
                "action": Action.ASK_FOR_INFORMATION_CHANGE,
                "domain_data": _information_change_data(
                    existing_information,
                    pending_changes,
                ),
            }
        )
    else:
        updates["pending_information_changes"] = {}

    return updates


__all__ = ["update_progress"]
