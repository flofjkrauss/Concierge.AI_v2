"""Tests for automatic local-model downloads."""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from configuration.application import ApplicationSettings
from utils import download_models as download_module
from utils.download_models import ModelDownloadError, ensure_models_available


def _settings(tmp_path: Path) -> ApplicationSettings:
    translation_model = tmp_path / "translation"
    intent_model = tmp_path / "intent"
    information_model = tmp_path / "information" / "extractor.gguf"
    return ApplicationSettings(
        translation_model=translation_model,
        translation_model_repository="models/translation",
        translation_model_download_url="https://models.test/translation",
        translation_model_files=("config.json", "weights.bin"),
        language_detector=tmp_path / "translation" / "lid.bin",
        language_detector_download_url="https://models.test/lid.bin",
        intent_detection_model=intent_model,
        intent_detection_model_repository="models/intent",
        intent_detection_model_download_url="https://models.test/intent",
        intent_detection_model_files=("config.json", "model.safetensors"),
        information_extraction_model_data_folder=information_model.parent,
        information_extraction_model=information_model,
        information_extraction_model_repository="models/information",
        information_extraction_model_filename=information_model.name,
        information_extraction_model_download_url=(
            "https://models.test/information/extractor.gguf"
        ),
    )


def test_downloads_only_missing_files_and_reports_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(tmp_path)
    settings.translation_model.mkdir(parents=True)
    (settings.translation_model / "config.json").write_text("existing")

    hub_download = Mock()
    monkeypatch.setattr(download_module, "hf_hub_download", hub_download)
    monkeypatch.setattr(
        download_module,
        "urlopen",
        Mock(return_value=BytesIO(b"language detector")),
    )

    ensure_models_available(settings)

    assert hub_download.call_args_list == [
        call(
            repo_id="models/translation",
            filename="weights.bin",
            local_dir=settings.translation_model,
        ),
        call(
            repo_id="models/intent",
            filename="config.json",
            local_dir=settings.intent_detection_model,
        ),
        call(
            repo_id="models/intent",
            filename="model.safetensors",
            local_dir=settings.intent_detection_model,
        ),
        call(
            repo_id="models/information",
            filename="extractor.gguf",
            local_dir=settings.information_extraction_model_data_folder,
        ),
    ]
    assert settings.language_detector.read_bytes() == b"language detector"
    output = capsys.readouterr().out
    assert "Downloading translation model file 'weights.bin'" in output
    assert "https://models.test/translation/weights.bin" in output
    assert "Downloading language detection model" in output
    assert "Downloading intent detection model file 'model.safetensors'" in output
    assert "Downloading information extraction model file 'extractor.gguf'" in output


def test_existing_model_files_do_not_trigger_downloads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(tmp_path)
    for directory, filenames in (
        (settings.translation_model, settings.translation_model_files),
        (settings.intent_detection_model, settings.intent_detection_model_files),
    ):
        directory.mkdir(parents=True)
        for filename in filenames:
            (directory / filename).write_text("existing")
    settings.language_detector.write_bytes(b"existing")
    settings.information_extraction_model.parent.mkdir(parents=True)
    settings.information_extraction_model.write_bytes(b"existing")

    hub_download = Mock()
    urlopen = Mock()
    monkeypatch.setattr(download_module, "hf_hub_download", hub_download)
    monkeypatch.setattr(download_module, "urlopen", urlopen)

    ensure_models_available(settings)

    hub_download.assert_not_called()
    urlopen.assert_not_called()
    assert capsys.readouterr().out == ""


def test_download_failure_reports_reason_and_stops_startup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        download_module,
        "hf_hub_download",
        Mock(side_effect=OSError("network unavailable")),
    )

    with pytest.raises(ModelDownloadError, match="network unavailable"):
        ensure_models_available(settings)

    error_output = capsys.readouterr().err
    assert "Failed to download translation model file 'config.json'" in error_output
    assert "network unavailable" in error_output
