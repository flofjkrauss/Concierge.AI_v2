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

    # Streamlit client server config
    #streamlit_host: str = "127.0.0.1"
    streamlit_host: str = "192.168.1.167"
    streamlit_port: int = 8501
    streamlit_headless: bool = True
    streamlit_gather_usage_stats: bool = False
    streamlit_development_mode: bool = False

    # loglevel config
    loglevel: str = "DEBUG"

    # database path
    db_path: Path = project_root / "data"

    # conversation settings
    msg_max_length: int = 250
    max_num_msg_with_intent_unknown: int = 5
    domain_language: str = "en"
