from configuration.application import ApplicationSettings
from configuration.fastapi import FastapiSettings


def test_fastapi_settings_point_to_repository_favicon() -> None:
    settings = FastapiSettings()

    assert settings.service_name == "FastAPI"
    assert settings.favicon_path == ApplicationSettings.project_root / "favicon.ico"
