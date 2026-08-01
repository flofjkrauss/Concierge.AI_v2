"""application wide configurations"""

from dataclasses import dataclass
from configuration.generic import Settings
from pathlib import Path


@dataclass(frozen=True)
class ApplicationSettings(Settings):
    """Runtime settings."""
    project_root: Path = Path(__file__).resolve().parents[2]
    app_name: str = "ConciergeAI"
    app_version: str = "0.01"
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True