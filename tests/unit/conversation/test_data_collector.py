from conversation.data_collector import DataCollector
from conversation.entities.information import Information
from conversation.value_object.information_fields import InformationField


def test_data_collector_stores_information_by_field() -> None:
    collector = DataCollector()
    first_name = Information(InformationField.FIRST_NAME, "Alex")
    email = Information(InformationField.EMAIL, "alex@example.com")

    collector.store_informations([first_name, email])

    assert collector.provide_data() == {
        InformationField.FIRST_NAME: first_name,
        InformationField.EMAIL: email,
    }


def test_data_collector_replaces_previous_value_for_same_field() -> None:
    collector = DataCollector()
    old = Information(InformationField.FIRST_NAME, "Alex")
    new = Information(InformationField.FIRST_NAME, "Sam")

    collector.store_informations([old])
    collector.store_informations([new])

    assert collector.provide_data()[InformationField.FIRST_NAME] is new
