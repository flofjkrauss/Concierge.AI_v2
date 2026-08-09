from fastapi import FastAPI

from utils.import_router import import_router


def test_import_router_registers_all_application_routes() -> None:
    app = FastAPI()

    import_router(app)

    paths = set(app.openapi()["paths"])
    assert {
        "/api/fastapi-status",
        "/api/availability/",
        "/api/bookings/{booking_id}",
        "/api/bookings/{booking_id}/cancel",
        "/api/bookings/request",
        "/api/information/{topic}",
        "/api/conversation/",
        "/api/conversation/{session_id}",
    } <= paths

    assert "/" not in paths
    assert "/favicon.ico" not in paths
