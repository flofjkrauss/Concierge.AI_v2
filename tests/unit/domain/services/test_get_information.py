from conftest import InMemoryDatabase

from domain.services.get_information import (
    get_hotel_address,
    get_hotel_name,
    get_information,
)
from domain.value_objects.information_topic import InformationTopic


def test_get_information_returns_stored_answer(database: InMemoryDatabase) -> None:
    database.information[InformationTopic.WIFI] = "Wi-Fi is complimentary."

    assert get_information(InformationTopic.WIFI, database) == (
        "Wi-Fi is complimentary."
    )


def test_get_information_returns_empty_string_when_missing(
    database: InMemoryDatabase,
) -> None:
    assert get_information(InformationTopic.PETS, database) == ""


def test_hotel_metadata_delegates_to_database(database: InMemoryDatabase) -> None:
    assert get_hotel_name(database) == "Harbour Light Hotel"
    assert get_hotel_address(database) == "1 Harbour Way, 12345 Seaside, DE"
