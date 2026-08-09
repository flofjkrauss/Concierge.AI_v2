from pathlib import Path
from unittest.mock import Mock

from utils.connect_database import connect


def test_connect_builds_json_database_from_application_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database = object()
    constructor = Mock(return_value=database)
    monkeypatch.setattr("utils.connect_database.ApplicationSettings.db_path", tmp_path)
    monkeypatch.setattr("utils.connect_database.JsonDatabase", constructor)

    assert connect() is database
    constructor.assert_called_once_with(data_directory=tmp_path)
