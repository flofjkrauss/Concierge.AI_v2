from unittest.mock import Mock

import pytest

from observability.log_messages import LOG_MSG


def test_debug_forwards_extra_fields_and_stacklevel(monkeypatch) -> None:
    logger = Mock()
    monkeypatch.setattr("observability.log_messages._LOGGER", logger)

    LOG_MSG.debug("message", extra={"request_id": "request-1"})

    logger.debug.assert_called_once_with(
        "message",
        extra={"request_id": "request-1"},
        stacklevel=2,
    )


@pytest.mark.parametrize(
    "method_name",
    ["info", "warning", "error", "critical", "exception"],
)
def test_log_methods_delegate_with_caller_stacklevel(
    monkeypatch,
    method_name: str,
) -> None:
    logger = Mock()
    monkeypatch.setattr("observability.log_messages._LOGGER", logger)

    getattr(LOG_MSG, method_name)("message")

    getattr(logger, method_name).assert_called_once_with("message", stacklevel=2)
