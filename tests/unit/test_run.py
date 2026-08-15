"""Tests for the combined API and client launcher."""

import socket
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

import run as run_module
from configuration.application import ApplicationSettings
from run import (
    _require_configured_ports_available,
    _start_processes,
    _streamlit_command,
    _uvicorn_command,
)


class FakeProcess:
    """Small process double for supervisor lifecycle tests."""

    def __init__(
        self,
        *,
        exit_code: int | None = None,
        interrupt_once: bool = False,
    ) -> None:
        self.exit_code = exit_code
        self.interrupt_once = interrupt_once
        self.terminated = False
        self.waited = False

    def poll(self) -> int | None:
        if self.interrupt_once:
            self.interrupt_once = False
            raise KeyboardInterrupt
        if self.terminated:
            return 0
        return self.exit_code

    def terminate(self) -> None:
        self.terminated = True

    def wait(self) -> int:
        self.waited = True
        return self.exit_code or 0


def test_uvicorn_command_uses_explicit_server_settings() -> None:
    settings = ApplicationSettings(host="0.0.0.0", port=9000, reload=False)

    command = _uvicorn_command(settings)

    assert command == [
        sys.executable,
        "-c",
        (
            "import uvicorn; uvicorn.run('run:app', host='0.0.0.0', "
            "port=9000, reload=False, log_config=None)"
        ),
    ]


def test_streamlit_command_uses_explicit_server_settings(tmp_path: Path) -> None:
    settings = ApplicationSettings(
        project_root=tmp_path,
        streamlit_host="0.0.0.0",
        streamlit_port=9501,
        streamlit_headless=False,
        streamlit_gather_usage_stats=True,
        streamlit_development_mode=False,
    )

    command = _streamlit_command(settings)

    assert command[1:] == [
        "-m",
        "streamlit",
        "run",
        str(tmp_path / "src" / "client" / "app.py"),
        "--global.developmentMode",
        "false",
        "--server.address",
        "0.0.0.0",
        "--server.port",
        "9501",
        "--server.headless",
        "false",
        "--browser.gatherUsageStats",
        "true",
    ]


def test_occupied_api_port_stops_before_starting_processes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        popen = Mock()
        monkeypatch.setattr("run.subprocess.Popen", popen)

        with pytest.raises(SystemExit) as exc_info:
            _start_processes(
                ApplicationSettings(
                    host="127.0.0.1",
                    port=port,
                    streamlit_host="127.0.0.1",
                    streamlit_port=0,
                )
            )

    assert exc_info.value.code == 1
    assert (
        f"API port 127.0.0.1:{port} is already in use."
        in capsys.readouterr().err
    )
    popen.assert_not_called()


def test_occupied_client_port_is_reported(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        with pytest.raises(SystemExit) as exc_info:
            _require_configured_ports_available(
                ApplicationSettings(
                    host="127.0.0.1",
                    port=0,
                    streamlit_host="127.0.0.1",
                    streamlit_port=port,
                )
            )

    assert exc_info.value.code == 1
    assert (
        f"client port 127.0.0.1:{port} is already in use."
        in capsys.readouterr().err
    )


def test_distinct_available_ports_pass_preflight() -> None:
    _require_configured_ports_available(
        ApplicationSettings(
            host="127.0.0.1",
            port=0,
            streamlit_host="127.0.0.1",
            streamlit_port=0,
        )
    )


def test_main_restarts_both_processes_when_one_exits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exited_api = FakeProcess(exit_code=1)
    first_client = FakeProcess()
    second_api = FakeProcess(interrupt_once=True)
    second_client = FakeProcess()
    start_processes = Mock(
        side_effect=[
            (exited_api, first_client),
            (second_api, second_client),
        ]
    )
    monkeypatch.setattr(run_module, "_start_processes", start_processes)
    monkeypatch.setattr("run.time.sleep", lambda _: None)

    run_module.main()

    assert start_processes.call_count == 2
    assert first_client.terminated is True
    assert exited_api.waited is True
    assert first_client.waited is True
    assert second_api.terminated is True
    assert second_client.terminated is True
