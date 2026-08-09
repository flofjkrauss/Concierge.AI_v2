from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from conftest import InMemoryDatabase

from api.dependencies import get_conversation_controller, get_database
from conversation.conversation_controller import ConversationController
from conversation.user_interaction import UserInteraction


def request_with_state(**state: object):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state)))


def test_get_database_returns_configured_database(
    database: InMemoryDatabase,
) -> None:
    request = request_with_state(database=database)

    assert get_database(request) is database  # type: ignore[arg-type]


def test_get_database_rejects_invalid_state() -> None:
    request = request_with_state(database=object())

    with pytest.raises(TypeError, match="No valid database"):
        get_database(request)  # type: ignore[arg-type]


def test_get_conversation_controller_returns_configured_controller() -> None:
    controller = ConversationController(Mock(), UserInteraction())
    request = request_with_state(conversation_controller=controller)

    assert get_conversation_controller(request) is controller  # type: ignore[arg-type]


def test_get_conversation_controller_rejects_invalid_state() -> None:
    request = request_with_state(conversation_controller=object())

    with pytest.raises(TypeError, match="Invalid conversation controller"):
        get_conversation_controller(request)  # type: ignore[arg-type]
