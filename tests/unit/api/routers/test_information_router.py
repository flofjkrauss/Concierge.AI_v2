from unittest.mock import Mock

import pytest
from conftest import InMemoryDatabase
from fastapi import HTTPException

from api.routers.information import read_topic
from domain.value_objects.information_topic import InformationTopic


def test_read_topic_normalizes_and_delegates(monkeypatch, database: InMemoryDatabase) -> None:
    get_information = Mock(return_value="Wi-Fi is complimentary.")
    monkeypatch.setattr("api.routers.information.get_information", get_information)

    assert read_topic(" WIFI ", database) == "Wi-Fi is complimentary."
    get_information.assert_called_once_with(
        topic=InformationTopic.WIFI,
        database=database,
    )


def test_read_topic_returns_404_for_unknown_topic(database: InMemoryDatabase) -> None:
    with pytest.raises(HTTPException) as error:
        read_topic("unknown", database)

    assert error.value.status_code == 404
    assert "No Information found" in error.value.detail
