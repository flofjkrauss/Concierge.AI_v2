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
    reload: bool = False

    # Streamlit client server config
    streamlit_host: str = "127.0.0.1"
    #streamlit_host: str = "192.168.1.167"
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

    primary_processing_unit: str = "cuda"
    fallback_processing_unit: str = "cpu"

    #translation
    conversation_path: Path = project_root / "src" / "conversation"
    translation_model_data_folder: Path = conversation_path / "models" / "translation" / "model_data"
    translation_model: Path = translation_model_data_folder / "m2m100_418M"
    language_detector: Path = translation_model_data_folder / "lid.176.bin"
    # fallback if cuda is not available, check logs to see that
    #translation_processing_unit = "cpu"
    translation_processing_unit = primary_processing_unit

    #chat
    base_url: str = "/api/conversation"
    conversation_endpoint: str = f"http://{host}:{port}{base_url}"

    #intent detection
    intent_processing_unit: str = primary_processing_unit
    intent_detection_model_data_folder: Path = conversation_path / "models" / "intent" / "model_data"
    intent_detection_model: Path = intent_detection_model_data_folder / "intent-classifier"
