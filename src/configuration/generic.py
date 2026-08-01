"""configurations for FastAPI service"""

from dataclasses import dataclass
from functools import cache
from typing import Self

@dataclass(frozen=True)
class Settings:
    """Runtime settings."""
    @classmethod
    @cache
    def get_settings(cls) -> Self:
        """Return the current settings."""
        return cls()