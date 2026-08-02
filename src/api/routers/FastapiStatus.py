"""FastAPI server status"""
import logging
logger = logging.getLogger(__name__)

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from configuration.fastapi import FastapiSettings


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
    logger.debug(
        "FastAPI status requested",
        extra={
            "event": "fastapi_status_requested",
            "service": settings.service_name,
            "status": status,
        })
    return StatusResponse(
        service=settings.service_name,
        status=status,
    )


