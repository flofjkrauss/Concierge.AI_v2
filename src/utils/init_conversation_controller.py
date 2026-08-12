"""Create the application-scoped conversation controller."""

from collections.abc import Callable
from time import perf_counter

import torch

from configuration.application import ApplicationSettings
from conversation.conversation_controller import ConversationController
from conversation.graph.builder import (
    build_conversation_graph,
    create_in_memory_checkpointer,
)
from conversation.models.information.information_extrator import InformationExtractor
from conversation.models.intent.intent_classifier import IntentClassifier
from conversation.models.translation.m2m100_translator import M2M100Translator
from conversation.user_interaction import UserInteraction
from database.interface import DatabaseInterface
from observability.log_messages import LOG_MSG


def _warm_up_models(
    warmups: tuple[tuple[str, Callable[[], None]], ...],
) -> None:
    """Warm each model independently without making startup less robust."""

    for model_name, warm_up in warmups:
        started = perf_counter()
        try:
            warm_up()
        except Exception:  # noqa: BLE001
            LOG_MSG.exception(f"{model_name} warm-up failed")
        else:
            duration = perf_counter() - started
            LOG_MSG.info(f"{model_name} warm-up completed in {duration:.2f}s")


def init(database: DatabaseInterface) -> ConversationController:
    """Build shared dependencies and one in-memory conversation graph."""

    if not isinstance(database, DatabaseInterface):
        raise TypeError("Invalid database parameter for conversation controller init")

    print("Loading models...")
    settings = ApplicationSettings.get_settings()
    torch.set_num_threads(settings.model_cpu_threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        # PyTorch permits setting this only before inter-op work starts.
        pass
    translator = M2M100Translator()
    intent_classifier = IntentClassifier()
    information_extractor = InformationExtractor()
    user_interaction = UserInteraction()
    checkpointer = create_in_memory_checkpointer()

    if settings.model_warmup_enabled:
        _warm_up_models(
            (
                ("M2M100 translator", translator.warm_up),
                ("Intent classifier", intent_classifier.warm_up),
                ("Information extractor", information_extractor.warm_up),
            )
        )

    graph = build_conversation_graph(
        database=database,
        translator=translator,
        intent_classifier=intent_classifier,
        information_extractor=information_extractor,
        user_interaction=user_interaction,
        checkpointer=checkpointer,
    )
    return ConversationController(
        graph=graph,
        user_interaction=user_interaction,
        translator=translator,
    )
