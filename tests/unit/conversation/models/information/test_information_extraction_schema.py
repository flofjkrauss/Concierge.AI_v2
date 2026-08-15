"""Tests for the structured information-extraction schema."""

from conversation.models.information.information_extraction_schema import (
    get_field_map,
    get_information_extraction_schema,
)
from conversation.value_object.information_fields import InformationField
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.room_category import RoomCategory


def test_schema_rejects_extra_fields_and_exposes_domain_enums() -> None:
    schema = get_information_extraction_schema()
    properties = schema["properties"]

    assert schema["additionalProperties"] is False
    assert properties["information_topic"]["enum"] == [
        topic.value for topic in InformationTopic
    ]
    assert properties["room_category"]["enum"] == [
        category.value for category in RoomCategory
    ]
    assert properties["confirmation"]["enum"] == ["yes", "no"]


def test_field_map_covers_every_schema_property() -> None:
    properties = get_information_extraction_schema()["properties"]
    field_map = get_field_map()

    assert set(properties) <= set(field_map)
    assert field_map["check_in"] is InformationField.CHECK_IN
