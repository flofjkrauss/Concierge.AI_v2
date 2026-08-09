from unittest.mock import Mock

import pytest
from conftest import InMemoryDatabase

from conversation.conversation_controller import ConversationController
from utils.init_conversation_controller import init


def test_init_builds_controller_with_shared_graph_dependencies(
    monkeypatch,
    database: InMemoryDatabase,
) -> None:
    graph = Mock()
    build_graph = Mock(return_value=graph)
    checkpointer = object()
    create_checkpointer = Mock(return_value=checkpointer)
    monkeypatch.setattr(
        "utils.init_conversation_controller.build_conversation_graph",
        build_graph,
    )
    monkeypatch.setattr(
        "utils.init_conversation_controller.create_in_memory_checkpointer",
        create_checkpointer,
    )

    controller = init(database)

    assert isinstance(controller, ConversationController)
    create_checkpointer.assert_called_once_with()
    call = build_graph.call_args.kwargs
    assert call["database"] is database
    assert call["checkpointer"] is checkpointer
    assert call["translator"].__class__.__name__ == "NoneTranslator"
    assert call["intent_classifier"].__class__.__name__ == "IntentClassifier"
    assert call["information_extractor"].__class__.__name__ == "InformationExtractor"
    assert call["user_interaction"].__class__.__name__ == "UserInteraction"


def test_init_rejects_invalid_database() -> None:
    with pytest.raises(TypeError, match="Invalid database parameter"):
        init(object())  # type: ignore[arg-type]
