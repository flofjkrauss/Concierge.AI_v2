import pytest

from conversation.graph.routing import (
    route_after_action,
    route_after_analysis,
    route_after_begin,
    route_after_confirmation,
    route_after_intent,
)
from conversation.graph.state import ConfirmationOutcome, DomainOperation
from conversation.value_object.action import Action


def test_route_after_begin_requires_parsed_message() -> None:
    assert route_after_begin({"parsed_message": object()}) == "process"  # type: ignore[arg-type]
    assert route_after_begin({"parsed_message": None}) == "finish"  # type: ignore[arg-type]


def test_route_after_analysis_prioritizes_termination_then_confirmation() -> None:
    assert route_after_analysis({"termination_requested": True}) == "terminate"  # type: ignore[arg-type]
    assert route_after_analysis({"expected_interaction": object()}) == "confirmation"  # type: ignore[arg-type]
    assert route_after_analysis({}) == "intent"  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "action",
    [
        Action.REPORT_INVALID_DATE,
        Action.REPORT_REUSED_DATE,
        Action.DISPLAY_INFO,
    ],
)
def test_route_after_analysis_builds_immediate_response(action: Action) -> None:
    assert route_after_analysis({"action": action}) == "response"  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("outcome", "route"),
    [
        (ConfirmationOutcome.CONFIRMED, "execute"),
        (ConfirmationOutcome.CHANGED, "fields"),
        (ConfirmationOutcome.INTERRUPTED, "intent"),
        (ConfirmationOutcome.DECLINED, "response"),
        (ConfirmationOutcome.UNCLEAR, "response"),
    ],
)
def test_route_after_confirmation_maps_outcome(outcome, route: str) -> None:
    assert route_after_confirmation({"confirmation_outcome": outcome}) == route  # type: ignore[arg-type]


def test_route_after_confirmation_requires_outcome() -> None:
    with pytest.raises(ValueError, match="requires an outcome"):
        route_after_confirmation({})  # type: ignore[arg-type]


def test_route_after_intent_uses_existing_action() -> None:
    assert route_after_intent({"action": Action.ASK_INTENT}) == "response"  # type: ignore[arg-type]
    assert route_after_intent({}) == "fields"  # type: ignore[arg-type]


def test_route_after_action_uses_selected_domain_operation() -> None:
    assert route_after_action(
        {"domain_operation": DomainOperation.GET_BOOKING}  # type: ignore[arg-type]
    ) == "execute"
    assert route_after_action({}) == "response"  # type: ignore[arg-type]
