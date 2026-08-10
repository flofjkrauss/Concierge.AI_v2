from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

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


@router.post("/{session_id}/terminate", status_code=status.HTTP_204_NO_CONTENT)
def terminate(
    session_id: str,
    controller: Annotated[
        ConversationController,
        Depends(get_conversation_controller),
    ],
) -> Response:
    """Terminate one conversation; repeated or unknown IDs are harmless."""

    controller.terminate_conversation(session_id=session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
