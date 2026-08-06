"""data collector for collecting data from chat sessions"""

from conversation.entities.information import Information
from conversation.value_object.information_fields import InformationField


class DataCollector:
    def __init__(self) -> None:
        self._informations: dict[InformationField, Information] = {}

    def store_informations(self, informations: list[Information]) -> None:
        for info in informations:
            self._informations[info.information_field] = info

    def provide_data(self) -> dict[InformationField, Information]:
        return self._informations