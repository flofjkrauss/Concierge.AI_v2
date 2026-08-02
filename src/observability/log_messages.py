"""Simple application logging interface."""

import logging

_LOGGER = logging.getLogger("concierge_ai")


class LogMessages:
    """Provide concise access to standard Python logging."""

    @staticmethod
    def debug(message: str) -> None:
        """Write a debug message."""
        _LOGGER.debug(message, stacklevel=2)

    @staticmethod
    def info(message: str) -> None:
        """Write an informational message."""
        _LOGGER.info(message, stacklevel=2)

    @staticmethod
    def warning(message: str) -> None:
        """Write a warning message."""
        _LOGGER.warning(message, stacklevel=2)

    @staticmethod
    def error(message: str) -> None:
        """Write an error message."""
        _LOGGER.error(message, stacklevel=2)

    @staticmethod
    def critical(message: str) -> None:
        """Write a critical message."""
        _LOGGER.critical(message, stacklevel=2)

    @staticmethod
    def exception(message: str) -> None:
        """Write an error including the current exception traceback."""
        _LOGGER.exception(message, stacklevel=2)


LOG_MSG = LogMessages()
