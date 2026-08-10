from pathlib import Path

from configuration.logging import LoggingSettings


def test_logging_settings_build_log_file_path(tmp_path: Path) -> None:
    settings = LoggingSettings(
        log_directory=tmp_path,
        log_file_name="application.jsonl",
    )

    assert settings.log_file_path == tmp_path / "application.jsonl"
