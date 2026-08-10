from unittest.mock import Mock

from api.routers.conversation import initialize, receive_message, terminate
from conversation.entities.interaction_response import InteractionResponse


def test_initialize_delegates_to_controller() -> None:
    response = InteractionResponse(True, "session-1")
    controller = Mock()
    controller.init_conversation.return_value = response

    assert initialize(controller) is response
    controller.init_conversation.assert_called_once_with()


def test_receive_message_delegates_session_and_message() -> None:
    response = InteractionResponse(True, "processed")
    controller = Mock()
    controller.process_message.return_value = response

    assert receive_message("session-1", "Hello", controller) is response
    controller.process_message.assert_called_once_with(
        session_id="session-1",
        message="Hello",
    )


def test_terminate_delegates_session_and_returns_no_content() -> None:
    controller = Mock()

    response = terminate("session-1", controller)

    controller.terminate_conversation.assert_called_once_with(
        session_id="session-1"
    )
    assert response.status_code == 204
    assert response.body == b""
