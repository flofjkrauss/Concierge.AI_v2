"""Simple application logging interface."""

import logging
from collections.abc import Mapping

_LOGGER = logging.getLogger("concierge_ai")


class LogMessages:
    """Provide concise access to standard Python logging."""

    @staticmethod
    def debug(message: str, extra: Mapping[str, object] | None = None) -> None:
        """Write a debug message."""
        _LOGGER.debug(message, extra=extra, stacklevel=2)

    @staticmethod
    def info(message: str, extra: Mapping[str, object] | None = None) -> None:
        """Write an informational message."""
        _LOGGER.info(message, extra=extra, stacklevel=2)

    @staticmethod
    def warning(message: str, extra: Mapping[str, object] | None = None) -> None:
        """Write a warning message."""
        _LOGGER.warning(message, extra=extra, stacklevel=2)

    @staticmethod
    def error(message: str, extra: Mapping[str, object] | None = None) -> None:
        """Write an error message."""
        _LOGGER.error(message, extra=extra, stacklevel=2)

    @staticmethod
    def critical(message: str, extra: Mapping[str, object] | None = None) -> None:
        """Write a critical message."""
        _LOGGER.critical(message, extra=extra, stacklevel=2)

    @staticmethod
    def exception(message: str, extra: Mapping[str, object] | None = None) -> None:
        """Write an error including the current exception traceback."""
        _LOGGER.exception(message, extra=extra, stacklevel=2)

LOG_MSG = LogMessages()
