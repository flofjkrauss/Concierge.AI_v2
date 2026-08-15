from configuration.application import ApplicationSettings


def test_application_settings_expose_project_defaults() -> None:
    settings = ApplicationSettings()

    assert settings.project_root.is_dir()
    assert (settings.project_root / "pyproject.toml").is_file()
    assert settings.db_path == settings.project_root / "data"
    assert settings.domain_language == "en"
    assert settings.streamlit_host == "127.0.0.1"
    assert settings.streamlit_port == 8501
    assert settings.streamlit_headless is True
    assert settings.streamlit_gather_usage_stats is False
    assert settings.streamlit_development_mode is False
    assert settings.translation_model_repository == "facebook/nllb-200-distilled-600M"
    assert settings.language_detector_download_url.startswith("https://")
    assert (
        settings.intent_detection_model_repository
        == "floriankrauss/intent_detector_concierge"
    )
    assert settings.information_extraction_model_repository == "Qwen/Qwen3-8B-GGUF"
