"""Tests for bounded API readiness polling."""

from contextlib import nullcontext
from unittest.mock import Mock

import pytest

from utils import wait_for_api as wait_module


def test_wait_for_api_returns_after_first_success(monkeypatch) -> None:
    urlopen = Mock(return_value=nullcontext())
    monkeypatch.setattr(wait_module.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(wait_module.time, "monotonic", Mock(side_effect=[0.0, 0.1]))

    wait_module.wait_for_api("http://hotel/status", timeout=1.0)

    urlopen.assert_called_once_with("http://hotel/status", timeout=1)


def test_wait_for_api_retries_transient_os_error(monkeypatch) -> None:
    urlopen = Mock(side_effect=[OSError("offline"), nullcontext()])
    sleep = Mock()
    monkeypatch.setattr(wait_module.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(
        wait_module.time,
        "monotonic",
        Mock(side_effect=[0.0, 0.1, 0.2]),
    )
    monkeypatch.setattr(wait_module.time, "sleep", sleep)

    wait_module.wait_for_api("http://hotel/status", timeout=1.0)

    assert urlopen.call_count == 2
    sleep.assert_called_once_with(0.2)


def test_wait_for_api_raises_when_deadline_expires(monkeypatch) -> None:
    urlopen = Mock(side_effect=OSError("offline"))
    monkeypatch.setattr(wait_module.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(
        wait_module.time,
        "monotonic",
        Mock(side_effect=[0.0, 0.1, 1.0]),
    )
    monkeypatch.setattr(wait_module.time, "sleep", Mock())

    with pytest.raises(RuntimeError, match="did not become ready"):
        wait_module.wait_for_api("http://hotel/status", timeout=1.0)
