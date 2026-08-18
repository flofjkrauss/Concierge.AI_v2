"""Tests for the trusted hotel-information topic wire value."""

import pytest

from conversation.value_object.information_topic_selection import (
    InformationTopicSelection,
)
from domain.value_objects.information_topic import InformationTopic


@pytest.mark.parametrize("topic", list(InformationTopic))
def test_information_topic_selection_round_trips(topic: InformationTopic) -> None:
    selection = InformationTopicSelection(topic)

    assert InformationTopicSelection.from_wire(selection.to_wire()) == selection


@pytest.mark.parametrize(
    "message",
    [
        "normal guest text",
        "__concierge_information_topic_v1__",
        "__concierge_information_topic_v1__|wifi|extra",
        "__concierge_information_topic_v1__|unknown",
    ],
)
def test_information_topic_selection_rejects_invalid_wire(message: str) -> None:
    assert InformationTopicSelection.from_wire(message) is None
