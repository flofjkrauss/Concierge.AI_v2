"""application wide configurations"""

import os
from dataclasses import dataclass
from pathlib import Path

from configuration.generic import Settings

_LOGICAL_CPU_COUNT = max(1, os.cpu_count() or 1)
_DEFAULT_INFERENCE_THREADS = max(1, _LOGICAL_CPU_COUNT // 2)


@dataclass(frozen=True)
class ApplicationSettings(Settings):
    """Runtime settings."""

    # general config
    project_root: Path = Path(__file__).resolve().parents[2]
    app_name: str = "ConciergeAI"
    app_version: str = "0.01"

    # webserver config
    host: str = "127.0.0.1"
    #host: str = "192.168.1.167"
    #host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    api_health_endpoint = "".join([
        "http://",
        host,
        ":",
        str(port),
        "/api/fastapi-status"
    ])
    health_check_timeout: float = 180.0

    # Streamlit client server config
    #streamlit_host: str = "127.0.0.1"
    #streamlit_host: str = "10.8.0.10"
    streamlit_host: str = host
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
    conversation_patience_interval_seconds: float = 8.0
    conversation_request_timeout_seconds: float | None = None

    primary_processing_unit: str = "cpu"
    fallback_processing_unit: str = "cpu"
    model_cpu_threads: int = _DEFAULT_INFERENCE_THREADS
    model_warmup_enabled: bool = True

    #translation
    conversation_path: Path = project_root / "src" / "conversation"
    translation_model_data_folder: Path = conversation_path / "models" / "translation" / "model_data"
    #translation_model: Path = translation_model_data_folder / "m2m100_418M"
    translation_model: Path = translation_model_data_folder / "nllb-200-distilled-600M"
    language_detector: Path = translation_model_data_folder / "lid.176.bin"
    # fallback if cuda is not available, check logs to see that
    #translation_processing_unit = "cpu"
    translation_processing_unit = primary_processing_unit
    translation_max_new_tokens: int = 96
    translation_num_beams: int = 1
    translation_cache_size: int = 256

    #chat
    base_url: str = "/api/conversation"
    conversation_endpoint: str = f"http://{host}:{port}{base_url}"

    #intent detection
    intent_processing_unit: str = primary_processing_unit
    intent_detection_model_data_folder: Path = conversation_path / "models" / "intent" / "model_data"
    intent_detection_model: Path = intent_detection_model_data_folder / "intent-classifier"
    intent_max_tokens: int = 128
    intent_cache_size: int = 512

    #information extraction
    information_processing_unit: str = primary_processing_unit
    information_extraction_model_data_folder: Path = conversation_path / "models" / "information" / "model_data"
    information_extraction_model: Path = information_extraction_model_data_folder / "Qwen3-8B-Q4_K_M.gguf"
    information_context_tokens: int = 2048
    information_batch_tokens: int = 512
    information_generation_threads: int = _DEFAULT_INFERENCE_THREADS
    information_batch_threads: int = _LOGICAL_CPU_COUNT
    information_max_tokens: int = 128
