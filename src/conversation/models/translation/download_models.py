"""Manual entry point for downloading all required local models."""

from utils.download_models import ensure_models_available


def download_models() -> None:
    """Download every missing model artifact."""

    ensure_models_available()


if __name__ == "__main__":
    download_models()
