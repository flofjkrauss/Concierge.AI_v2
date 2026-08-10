from conversation.value_object.information_fields import InformationField
from conversation.value_object.intent import Intent
from conversation.value_object.intent_information_mapping import IntentInformationMapper


def test_availability_fields_are_complete_and_ordered() -> None:
    assert IntentInformationMapper.determine_fields(Intent.AVAILABILITY_CHECK) == [
        InformationField.CHECK_IN,
        InformationField.CHECK_OUT,
        InformationField.GUEST_COUNT,
        InformationField.ACCESSIBLE,
    ]


def test_booking_request_includes_booking_and_customer_fields() -> None:
    assert IntentInformationMapper.determine_fields(Intent.BOOKING_REQUEST) == [
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
    ]


def test_lookup_and_cancellation_use_guest_identity_and_check_in() -> None:
    assert IntentInformationMapper.determine_fields(Intent.BOOKING_CHECK) == [
        InformationField.LAST_NAME,
        InformationField.EMAIL,
        InformationField.CHECK_IN,
    ]
    assert IntentInformationMapper.determine_fields(Intent.BOOKING_CANCELLATION) == [
        InformationField.LAST_NAME,
        InformationField.EMAIL,
        InformationField.CHECK_IN,
    ]


def test_information_request_requires_topic() -> None:
    assert IntentInformationMapper.determine_fields(Intent.INFORMATION_REQUEST) == [
        InformationField.INFORMATION_TOPIC
    ]


def test_non_business_intents_require_no_information() -> None:
    assert (
        IntentInformationMapper.determine_fields(Intent.CONVERSATION_INITIATION) == []
    )
    assert IntentInformationMapper.determine_fields(Intent.UNKNOWN) == []
