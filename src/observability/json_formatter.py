"""Minimal JSON formatter for application logs."""

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Format a log record as a minimal JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        """Return the formatted log record."""
        timestamp = datetime.fromtimestamp(
            record.created,
            tz=UTC,
        ).isoformat(timespec="milliseconds")

        message = record.getMessage()

        if record.exc_info is not None:
            exception_text = self.formatException(record.exc_info)
            message = f"{message}\n{exception_text}"

        return json.dumps(
            {
                "timestamp": timestamp.replace("+00:00", "Z"),
                "level": record.levelname,
                "module": record.module,
                "method": record.funcName,
                "message": message,
            },
            ensure_ascii=False,
        )
