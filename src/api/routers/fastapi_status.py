"""FastAPI server status"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from configuration.fastapi import FastapiSettings
from observability import LOG_MSG

router = APIRouter(prefix="/api", tags=["server-status"])


class StatusResponse(BaseModel):
    """Response returned by the health endpoint."""

    service: str
    status: str


@router.get("/fastapi-status", response_model=StatusResponse)
def read_status(
    settings: Annotated[FastapiSettings, Depends(FastapiSettings.get_settings)],
) -> StatusResponse:
    """Return the current service health status."""
    status = "healthy"
    LOG_MSG.debug(f"FastAPI status requested. Status is: {status}")

    return StatusResponse(
        service=settings.service_name,
        status=status,
    )
