"""Application logging settings."""

from dataclasses import dataclass
from pathlib import Path

from configuration.application import ApplicationSettings
from configuration.generic import Settings


@dataclass(frozen=True)
class LoggingSettings(Settings):
    """Runtime settings for application logging."""

    log_level: str = ApplicationSettings.loglevel
    log_directory: Path = (ApplicationSettings.project_root / "logs")
    log_file_name: str = "concierge-ai.jsonl"

    max_file_size_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5

    @property
    def log_file_path(self) -> Path:
        """Return the complete application log file path."""
        return self.log_directory / self.log_file_name