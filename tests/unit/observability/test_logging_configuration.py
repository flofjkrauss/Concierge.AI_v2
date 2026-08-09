from __future__ import annotations

import logging
from pathlib import Path

import pytest

from configuration.logging import LoggingSettings
from observability.json_formatter import JsonFormatter
from observability.logging_configuration import (
    _handler_is_configured,
    _resolve_log_level,
    configure_logging,
)


def test_resolve_log_level_is_case_insensitive() -> None:
    assert _resolve_log_level("debug") == logging.DEBUG
    assert _resolve_log_level("WARNING") == logging.WARNING


def test_resolve_log_level_rejects_unknown_name() -> None:
    with pytest.raises(TypeError, match="Invalid logging level"):
        _resolve_log_level("verbose")


def test_handler_detection_uses_configured_name() -> None:
    logger = logging.getLogger("test.handler-detection")
    handler = logging.NullHandler()
    handler.set_name("concierge_ai_json_file")
    logger.addHandler(handler)

    try:
        assert _handler_is_configured(logger)
    finally:
        logger.removeHandler(handler)


def test_configure_logging_adds_single_json_file_handler(
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = logging.getLogger()
    original_level = root.level
    original_handlers = list(root.handlers)
    child_names = ["uvicorn", "uvicorn.error", "uvicorn.access", "asyncio"]
    child_levels = {name: logging.getLogger(name).level for name in child_names}
    settings = LoggingSettings(
        log_level="INFO",
        log_directory=tmp_path,
        log_file_name="test.jsonl",
        max_file_size_bytes=1024,
        backup_count=1,
    )
    monkeypatch.setattr(
        "observability.logging_configuration.LoggingSettings.get_settings",
        lambda: settings,
    )

    try:
        configure_logging()
        configure_logging()

        added = [
            handler
            for handler in root.handlers
            if handler not in original_handlers
        ]
        assert len(added) == 1
        assert isinstance(added[0].formatter, JsonFormatter)
        assert root.level == logging.INFO
        assert all(logging.getLogger(name).level == logging.WARNING for name in child_names)
    finally:
        for handler in list(root.handlers):
            if handler not in original_handlers:
                root.removeHandler(handler)
                handler.close()
        root.setLevel(original_level)
        for name, level in child_levels.items():
            logging.getLogger(name).setLevel(level)
