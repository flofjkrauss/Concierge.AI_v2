"""Service for retrieving hotel information."""

from database.interface import DatabaseInterface
from domain.value_objects.information_topic import InformationTopic
from observability import LOG_MSG


def get_information(
    topic: InformationTopic,
    database: DatabaseInterface,
) -> str | None:
    """Return the hotel information associated with the given key."""
    information = database.get_information(topic)

    if information is None:
        LOG_MSG.debug(
            f"No hotel information was found for key {topic}.")

    return information