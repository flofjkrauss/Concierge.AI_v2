"""Tests for the application entry point."""

from unittest.mock import Mock

from pytest import MonkeyPatch

import run


def test_main_starts_uvicorn(
    monkeypatch: MonkeyPatch,
) -> None:
    """main should start the configured Uvicorn server."""
    uvicorn_run = Mock()

    monkeypatch.setattr(
        "run.uvicorn.run",
        uvicorn_run,
    )

    run.main()

    uvicorn_run.assert_called_once_with(
        "run:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_config=None,
    )