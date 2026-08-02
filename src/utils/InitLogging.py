import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.configuration.application import ApplicationSettings

from src.observability.logging_configuration import configure_logging


def init_logging() -> logging:
    global logger
    logger = logging.getLogger(__name__)
    configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Handle application startup and shutdown."""
    application_settings = ApplicationSettings.get_settings()

    logger.info(
        "Application started",
        extra={
            "event": "application_started",
            "application": application_settings.app_name,
            "version": application_settings.app_version,
        },
    )

    yield

    logger.info(
        "Application stopped",
        extra={
            "event": "application_stopped",
            "application": application_settings.app_name,
            "version": application_settings.app_version,
        },
    )