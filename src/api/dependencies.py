from fastapi import Request

from database.interface import DatabaseInterface


def get_database(request: Request) -> DatabaseInterface:
    """Return the configured database implementation."""

    database = request.app.state.database

    if not isinstance(database, DatabaseInterface):
        raise TypeError(
            "No valid database implementation is configured"
        )

    return database