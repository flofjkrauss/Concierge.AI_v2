from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from configuration.application import ApplicationSettings
from observability.log_messages import LOG_MSG
from observability.logging_configuration import configure_logging


def init_logging() -> None:
    configure_logging()



@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Handle application startup and shutdown."""
    application_settings = ApplicationSettings.get_settings()

    LOG_MSG.info(
        f"Application started. App: {application_settings.app_name}, Version: {application_settings.app_version}"
    )

    yield

    LOG_MSG.info(
        f"Application stopped. App: {application_settings.app_name}, Version: {application_settings.app_version}"
    )
