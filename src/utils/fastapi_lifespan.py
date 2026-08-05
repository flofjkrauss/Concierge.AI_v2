from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from configuration.application import ApplicationSettings
from observability.log_messages import LOG_MSG
from observability.logging_configuration import configure_logging
from utils.connect_database import connect as connect_database
from utils.init_conversation_controller import init as init_controller


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle application startup and shutdown."""
    application_settings = ApplicationSettings.get_settings()
    configure_logging()
    
    app.state.database = connect_database()
    app.state.conversation_controller = init_controller(database=app.state.database)

    LOG_MSG.info(
        f"Application started. App: {application_settings.app_name}, Version: {application_settings.app_version}"
    )

    yield

    LOG_MSG.info(
        f"Application stopped. App: {application_settings.app_name}, Version: {application_settings.app_version}"
    )
