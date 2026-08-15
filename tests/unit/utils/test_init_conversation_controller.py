from unittest.mock import Mock

import pytest
from conftest import InMemoryDatabase

from conversation.conversation_controller import ConversationController
from utils import init_conversation_controller as controller_module
from utils.init_conversation_controller import init


def test_init_builds_controller_with_shared_graph_dependencies(
    monkeypatch,
    database: InMemoryDatabase,
) -> None:
    graph = Mock()
    build_graph = Mock(return_value=graph)
    checkpointer = object()
    create_checkpointer = Mock(return_value=checkpointer)
    translator = Mock()
    classifier = Mock()
    extractor = Mock()
    translator_factory = Mock(return_value=translator)
    classifier_factory = Mock(return_value=classifier)
    extractor_factory = Mock(return_value=extractor)
    monkeypatch.setattr(
        "utils.init_conversation_controller.build_conversation_graph",
        build_graph,
    )
    monkeypatch.setattr(
        "utils.init_conversation_controller.create_in_memory_checkpointer",
        create_checkpointer,
    )
    monkeypatch.setattr(controller_module, "NLLBTranslator", translator_factory)
    monkeypatch.setattr(controller_module, "IntentClassifier", classifier_factory)
    monkeypatch.setattr(
        controller_module,
        "InformationExtractor",
        extractor_factory,
    )

    controller = init(database)

    assert isinstance(controller, ConversationController)
    create_checkpointer.assert_called_once_with()
    call = build_graph.call_args.kwargs
    assert call["database"] is database
    assert call["checkpointer"] is checkpointer
    assert call["translator"] is translator
    assert call["intent_classifier"] is classifier
    assert call["information_extractor"] is extractor
    assert call["user_interaction"].__class__.__name__ == "UserInteraction"
    assert controller._translator is translator
    translator.warm_up.assert_called_once_with()
    classifier.warm_up.assert_called_once_with()
    extractor.warm_up.assert_called_once_with()


def test_init_rejects_invalid_database() -> None:
    with pytest.raises(TypeError, match="Invalid database parameter"):
        init(object())  # type: ignore[arg-type]
