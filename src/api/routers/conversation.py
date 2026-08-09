from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import get_conversation_controller
from conversation.conversation_controller import ConversationController
from conversation.entities.interaction_response import InteractionResponse

router = APIRouter(
    prefix="/api/conversation",
    tags=["conversation"],
)


@router.post("/", response_model=None)
def initialize(
    controller: Annotated[
        ConversationController,
        Depends(get_conversation_controller),
    ],
) -> InteractionResponse:


    return controller.init_conversation()

@router.post("/{session_id}", response_model=None)
def receive_message(
    session_id: str,
    message: str,
    controller: Annotated[
        ConversationController,
        Depends(get_conversation_controller),
    ],
) -> InteractionResponse:
    return controller.process_message(session_id=session_id, message=message)
