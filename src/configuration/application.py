"""application wide configurations"""

from dataclasses import dataclass
from pathlib import Path

from configuration.generic import Settings


@dataclass(frozen=True)
class ApplicationSettings(Settings):
    """Runtime settings."""

    # general config
    project_root: Path = Path(__file__).resolve().parents[2]
    app_name: str = "ConciergeAI"
    app_version: str = "0.01"

    # webserver config
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True

    # loglevel config
    loglevel: str = "DEBUG"

    # database path
    db_path: Path = project_root / "data"
