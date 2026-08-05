"""Tests for the application startup."""

"""Tests for application startup and shutdown."""

import asyncio

from fastapi import FastAPI
from pytest import MonkeyPatch

from observability.log_messages import LOG_MSG
from utils.fastapi_lifespan import lifespan


def test_lifespan_logs_startup_and_shutdown(
    monkeypatch: MonkeyPatch,
) -> None:
    """The application should log startup and shutdown messages."""
    messages: list[str] = []

    monkeypatch.setattr(
        LOG_MSG,
        "info",
        messages.append,
    )

    async def run_lifespan() -> None:
        app = FastAPI()

        async with lifespan(app):
            assert messages == [
                "Application started. App: ConciergeAI, Version: 0.01",
            ]

        assert messages == [
            "Application started. App: ConciergeAI, Version: 0.01",
            "Application stopped. App: ConciergeAI, Version: 0.01",
        ]

    asyncio.run(run_lifespan())
