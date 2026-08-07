from api.routers.fastapi_status import read_status
from configuration.fastapi import FastapiSettings


def test_read_status_returns_service_health() -> None:
    response = read_status(FastapiSettings(service_name="Test API"))

    assert response.service == "Test API"
    assert response.status == "healthy"
