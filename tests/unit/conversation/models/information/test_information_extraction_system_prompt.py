"""Tests for information-extraction prompt boundaries."""

from conversation.models.information.information_extraction_system_prompt import (
    get_system_prompt,
)
from domain.value_objects.information_topic import InformationTopic
from domain.value_objects.room_category import RoomCategory


def test_system_prompt_lists_current_domain_values_and_no_guessing_rules() -> None:
    prompt = get_system_prompt()

    assert "Never guess." in prompt
    assert "CURRENT user message" in prompt
    assert "Return only JSON" in prompt
    for topic in InformationTopic:
        assert topic.value in prompt
    for category in RoomCategory:
        assert category.value in prompt
