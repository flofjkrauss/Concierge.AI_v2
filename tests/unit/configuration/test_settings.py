from dataclasses import dataclass
from pathlib import Path

from configuration.application import ApplicationSettings
from configuration.fastapi import FastapiSettings
from configuration.generic import Settings
from configuration.logging import LoggingSettings


def test_settings_factory_is_cached_per_settings_class() -> None:
    @dataclass(frozen=True)
    class ExampleSettings(Settings):
        value: str = "example"

    assert ExampleSettings.get_settings() is ExampleSettings.get_settings()


def test_application_settings_expose_project_defaults() -> None:
    settings = ApplicationSettings()

    assert settings.project_root.name == "Concierge.AI_v2"
    assert settings.db_path == settings.project_root / "data"
    assert settings.domain_language == "en"
    assert settings.msg_max_length > 0


def test_fastapi_settings_point_to_repository_favicon() -> None:
    settings = FastapiSettings()

    assert settings.service_name == "FastAPI"
    assert settings.favicon_path == ApplicationSettings.project_root / "favicon.ico"


def test_logging_settings_build_log_file_path(tmp_path: Path) -> None:
    settings = LoggingSettings(
        log_directory=tmp_path,
        log_file_name="application.jsonl",
    )

    assert settings.log_file_path == tmp_path / "application.jsonl"
