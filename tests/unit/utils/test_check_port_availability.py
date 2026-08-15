"""Tests for configured API and client port preflight checks."""

import socket

import pytest

from configuration.application import ApplicationSettings
from utils.check_port_availability import require_configured_ports_available


def test_occupied_client_port_is_reported(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        with pytest.raises(SystemExit) as exc_info:
            require_configured_ports_available(
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
    require_configured_ports_available(
        ApplicationSettings(
            host="127.0.0.1",
            port=0,
            streamlit_host="127.0.0.1",
            streamlit_port=0,
        )
    )


def test_duplicate_configured_port_is_rejected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        require_configured_ports_available(
            ApplicationSettings(
                host="127.0.0.1",
                port=8123,
                streamlit_host="127.0.0.1",
                streamlit_port=8123,
            )
        )

    assert exc_info.value.code == 1
    assert "client port 127.0.0.1:8123 is already in use" in (
        capsys.readouterr().err
    )
