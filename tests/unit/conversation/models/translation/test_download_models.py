"""Tests for deterministic local-model download orchestration."""

from io import BytesIO
from unittest.mock import Mock, call

from conversation.models.translation import download_models as download_module


def test_download_models_requests_manifest_and_writes_language_model(
    monkeypatch,
    tmp_path,
) -> None:
    model_dir = tmp_path / "translator"
    language_path = tmp_path / "lid.176.bin"
    hub_download = Mock()
    urlopen = Mock(return_value=BytesIO(b"language-model"))
    monkeypatch.setattr(download_module, "_TRANSLATION_MODEL_DIR", model_dir)
    monkeypatch.setattr(download_module, "_LANGUAGE_MODEL_PATH", language_path)
    monkeypatch.setattr(download_module, "_TRANSLATION_FILES", ("a.json", "b.bin"))
    monkeypatch.setattr(download_module, "hf_hub_download", hub_download)
    monkeypatch.setattr(download_module, "urlopen", urlopen)

    download_module.download_models()

    assert hub_download.call_args_list == [
        call(
            repo_id=download_module._TRANSLATION_REPOSITORY,
            filename="a.json",
            local_dir=model_dir,
        ),
        call(
            repo_id=download_module._TRANSLATION_REPOSITORY,
            filename="b.bin",
            local_dir=model_dir,
        ),
    ]
    assert language_path.read_bytes() == b"language-model"


def test_download_models_reuses_existing_language_model(monkeypatch, tmp_path) -> None:
    language_path = tmp_path / "lid.176.bin"
    language_path.write_bytes(b"existing")
    urlopen = Mock()
    monkeypatch.setattr(download_module, "_TRANSLATION_MODEL_DIR", tmp_path / "model")
    monkeypatch.setattr(download_module, "_LANGUAGE_MODEL_PATH", language_path)
    monkeypatch.setattr(download_module, "_TRANSLATION_FILES", ())
    monkeypatch.setattr(download_module, "urlopen", urlopen)

    download_module.download_models()

    urlopen.assert_not_called()
