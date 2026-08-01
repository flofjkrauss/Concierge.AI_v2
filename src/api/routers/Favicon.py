"""FastAPI server status"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from configuration.fastapi import FastapiSettings

router = APIRouter(prefix="")


class StatusResponse(BaseModel):
    """Response returned by the health endpoint."""

    service: str
    status: str


@router.get("/favicon.ico", include_in_schema=False) #include_in_schema=False removes it from auto-generated documentation
def favicon(
    settings: Annotated[FastapiSettings, Depends(FastapiSettings.get_settings)],
) -> FileResponse:
    """Return the application favicon."""
    return FileResponse(
        path=settings.favicon_path,
        media_type="image/vnd.microsoft.icon",
    )
