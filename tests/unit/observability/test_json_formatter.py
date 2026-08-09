from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from uuid import UUID

from domain.value_objects.booking_status import BookingStatus
from observability.json_formatter import JsonFormatter


def make_record(message: str = "Hello %s") -> logging.LogRecord:
    record = logging.LogRecord(
        name="concierge_ai",
        level=logging.INFO,
        pathname="module.py",
        lineno=10,
        msg=message,
        args=("world",) if "%s" in message else (),
        exc_info=None,
        func="run",
    )
    record.created = 1_893_456_000.123
    return record


def test_json_formatter_outputs_structured_core_fields() -> None:
    payload = json.loads(JsonFormatter().format(make_record()))

    assert payload["timestamp"].endswith("Z")
    assert payload["level"] == "INFO"
    assert payload["module"] == "module"
    assert payload["method"] == "run"
    assert payload["message"] == "Hello world"


def test_json_formatter_includes_extra_fields() -> None:
    record = make_record("Request")
    record.request_id = "request-1"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "request-1"
    assert "pathname" not in payload


def test_json_formatter_appends_exception_text() -> None:
    try:
        raise ValueError("broken")
    except ValueError:
        record = make_record("Failed")
        record.exc_info = sys.exc_info()

    payload = json.loads(JsonFormatter().format(record))

    assert "Failed" in payload["message"]
    assert "ValueError: broken" in payload["message"]


def test_json_formatter_serializes_common_application_values(tmp_path: Path) -> None:
    class ExampleEnum(Enum):
        VALUE = "value"

    @dataclass
    class Payload:
        name: str

    record = make_record("Values")
    record.values = {
        "enum": BookingStatus.CONFIRMED,
        "plain_enum": ExampleEnum.VALUE,
        "datetime": datetime(2030, 1, 1, tzinfo=UTC),
        "date": date(2030, 1, 2),
        "uuid": UUID("12345678-1234-5678-1234-567812345678"),
        "path": tmp_path,
        "dataclass": Payload("example"),
        "set": {"a", "b"},
    }

    values = json.loads(JsonFormatter().format(record))["values"]

    assert values["enum"] == "confirmed"
    assert values["plain_enum"] == "value"
    assert values["datetime"] == "2030-01-01T00:00:00Z"
    assert values["date"] == "2030-01-02"
    assert values["uuid"] == "12345678-1234-5678-1234-567812345678"
    assert values["path"] == str(tmp_path)
    assert values["dataclass"] == {"name": "example"}
    assert set(values["set"]) == {"a", "b"}


def test_json_formatter_falls_back_to_string_representation() -> None:
    class Unknown:
        def __str__(self) -> str:
            return "unknown"

    record = make_record("Value")
    record.value = Unknown()

    assert json.loads(JsonFormatter().format(record))["value"] == "unknown"
