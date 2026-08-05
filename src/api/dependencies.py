from fastapi import Request

from conversation.conversation_controller import ConversationController
from database.interface import DatabaseInterface


def get_database(request: Request) -> DatabaseInterface:
    """Return the configured database implementation."""
    database = request.app.state.database

    if not isinstance(database, DatabaseInterface):
        raise TypeError(
            "No valid database implementation is configured"
        )

    return database

def get_conversation_controller(request: Request) -> ConversationController:
    """Return the conversation controller instance"""
    controller = request.app.state.conversation_controller

    if not isinstance(controller, ConversationController):
        raise TypeError(
            "Invalid conversation controller instance"
        )
    return controller