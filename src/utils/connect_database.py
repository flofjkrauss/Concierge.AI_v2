
from configuration.application import ApplicationSettings
from database.json_database import JsonDatabase


def connect() -> JsonDatabase:
    database = JsonDatabase(
        data_directory=ApplicationSettings.db_path
    )
    return database