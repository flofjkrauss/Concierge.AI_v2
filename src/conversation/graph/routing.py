"""Side-effect-free routing decisions for the conversation graph."""

from typing import Literal

from conversation.graph.state import ConfirmationOutcome, ConversationState
from conversation.value_object.action import Action

AfterBeginRoute = Literal["process", "finish"]
AfterAnalysisRoute = Literal["terminate", "confirmation", "intent", "response"]
AfterConfirmationRoute = Literal["execute", "fields", "intent", "response"]
AfterIntentRoute = Literal["fields", "response"]
AfterActionRoute = Literal["execute", "response"]


def route_after_begin(state: ConversationState) -> AfterBeginRoute:
    """Continue only when ``begin_turn`` produced a valid user message."""

    if state.get("parsed_message") is None:
        return "finish"
    return "process"


def route_after_analysis(state: ConversationState) -> AfterAnalysisRoute:
    """Handle termination and pending confirmations before normal intent flow."""

    if state.get("termination_requested", False):
        return "terminate"
    if state.get("action") in {
        Action.REPORT_INVALID_DATE,
        Action.DISPLAY_INFO,
    }:
        return "response"
    if state.get("expected_interaction") is not None:
        if state.get("action") == Action.ASK_FOR_INFORMATION_CHANGE:
            return "response"
        return "confirmation"
    return "intent"


def route_after_confirmation(state: ConversationState) -> AfterConfirmationRoute:
    """Route the deterministic result of confirmation interpretation."""

    match state.get("confirmation_outcome"):
        case ConfirmationOutcome.CONFIRMED:
            return "execute"
        case ConfirmationOutcome.CHANGED:
            return "fields"
        case (
            ConfirmationOutcome.INFORMATION_CHANGE_CONFIRMED
            | ConfirmationOutcome.INFORMATION_CHANGE_DECLINED
        ):
            return "fields"
        case ConfirmationOutcome.INTERRUPTED:
            return "intent"
        case ConfirmationOutcome.DECLINED | ConfirmationOutcome.UNCLEAR:
            return "response"
        case None:
            raise ValueError("Confirmation routing requires an outcome")


def route_after_intent(state: ConversationState) -> AfterIntentRoute:
    """Skip field calculation for immediate conversation responses."""

    if state.get("action") is not None:
        return "response"
    return "fields"


def route_after_action(state: ConversationState) -> AfterActionRoute:
    """Execute a selected domain operation or build the selected response."""

    if state.get("domain_operation") is not None:
        return "execute"
    return "response"
