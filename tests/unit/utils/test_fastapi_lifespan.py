import asyncio
from unittest.mock import Mock

from fastapi import FastAPI

from configuration.application import ApplicationSettings
from utils.fastapi_lifespan import lifespan


def test_lifespan_configures_dependencies_and_logs_boundaries(monkeypatch) -> None:
    app = FastAPI()
    database = object()
    controller = object()
    configure = Mock()
    connect = Mock(return_value=database)
    initialize = Mock(return_value=controller)
    info = Mock()
    settings = ApplicationSettings(app_name="Test App", app_version="1.2.3")
    monkeypatch.setattr("utils.fastapi_lifespan.configure_logging", configure)
    monkeypatch.setattr("utils.fastapi_lifespan.connect_database", connect)
    monkeypatch.setattr("utils.fastapi_lifespan.init_controller", initialize)
    monkeypatch.setattr(
        "utils.fastapi_lifespan.ApplicationSettings.get_settings",
        Mock(return_value=settings),
    )
    monkeypatch.setattr("utils.fastapi_lifespan.LOG_MSG.info", info)

    async def run_lifespan() -> None:
        async with lifespan(app):
            assert app.state.database is database
            assert app.state.conversation_controller is controller
            assert info.call_count == 1

    asyncio.run(run_lifespan())

    configure.assert_called_once_with()
    connect.assert_called_once_with()
    initialize.assert_called_once_with(database=database)
    assert info.call_count == 2
    assert "Application started" in info.call_args_list[0].args[0]
    assert "Application stopped" in info.call_args_list[1].args[0]
