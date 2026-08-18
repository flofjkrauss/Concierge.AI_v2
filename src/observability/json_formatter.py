"""JSON formatter for structured application logs."""

import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

_STANDARD_LOG_RECORD_ATTRIBUTES = frozenset(
    logging.makeLogRecord({}).__dict__.keys()
) | {
    "asctime",
    "message",
}


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON objects."""

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

        log_data: dict[str, Any] = {
            "timestamp": timestamp.replace("+00:00", "Z"),
            "level": record.levelname,
            "module": record.module,
            "method": record.funcName,
            "message": message,
        }

        extra_fields = self._extract_extra_fields(record)

        for key, value in extra_fields.items():
            # Keep the formatter-owned fields authoritative.
            if key not in log_data:
                log_data[key] = value

        return json.dumps(
            log_data,
            ensure_ascii=False,
            default=self._serialize_value,
        )

    @staticmethod
    def _extract_extra_fields(
        record: logging.LogRecord,
    ) -> dict[str, Any]:
        """Return attributes added through logging's extra argument."""
        extra_fields: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRIBUTES and not key.startswith("_"):
                extra_fields[key] = value

        return extra_fields

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Convert common application objects into JSON-compatible values."""
        if isinstance(value, Enum):
            return value.value

        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, Path):
            return str(value)

        if is_dataclass(value) and not isinstance(value, type):
            return asdict(value)

        if isinstance(value, set):
            return list(value)

        return str(value)
