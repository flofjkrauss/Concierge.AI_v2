"""Central application logging configuration."""

import logging
from logging.handlers import RotatingFileHandler

from configuration.logging import LoggingSettings
from observability.json_formatter import JsonFormatter

_HANDLER_NAME = "concierge_ai_json_file"


def configure_logging() -> None:
    """Configure structured file logging for the application."""
    settings = LoggingSettings.get_settings()

    settings.log_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(_resolve_log_level(settings.log_level))

    if _handler_is_configured(root_logger):
        return

    file_handler = RotatingFileHandler(
        filename=settings.log_file_path,
        maxBytes=settings.max_file_size_bytes,
        backupCount=settings.backup_count,
        encoding="utf-8",
    )

    file_handler.set_name(_HANDLER_NAME)
    file_handler.setLevel(_resolve_log_level(settings.log_level))
    file_handler.setFormatter(JsonFormatter())

    root_logger.addHandler(file_handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def _handler_is_configured(logger: logging.Logger) -> bool:
    """Return whether the ConciergeAI file handler already exists."""
    return any(handler.get_name() == _HANDLER_NAME for handler in logger.handlers)


def _resolve_log_level(level_name: str) -> int:
    """Convert a configured log level name into its numeric value."""
    level = getattr(logging, level_name.upper(), None)

    if not isinstance(level, int):
        raise TypeError(f"Invalid logging level: {level_name}")

    return level
