"""Tests for the backwards-compatible model download entry point."""

from unittest.mock import Mock

from conversation.models.translation import download_models as download_module


def test_download_models_delegates_to_shared_utility(monkeypatch) -> None:
    ensure_models_available = Mock()
    monkeypatch.setattr(
        download_module,
        "ensure_models_available",
        ensure_models_available,
    )

    download_module.download_models()

    ensure_models_available.assert_called_once_with()
