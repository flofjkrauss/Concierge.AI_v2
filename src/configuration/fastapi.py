"""configurations for FastAPI service"""

from dataclasses import dataclass
from pathlib import Path

from configuration.application import ApplicationSettings
from configuration.generic import Settings


@dataclass(frozen=True)
class FastapiSettings(Settings):
    """Runtime settings."""

    service_name: str = "FastAPI"
    favicon_path: Path = ApplicationSettings.project_root / "favicon.ico"
