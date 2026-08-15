"""Download missing local model artifacts before application startup."""

import sys
from collections.abc import Callable
from functools import partial
from pathlib import Path
from shutil import copyfileobj
from urllib.request import urlopen

from huggingface_hub import hf_hub_download

from configuration.application import ApplicationSettings


class ModelDownloadError(RuntimeError):
    """Raised when a required model artifact cannot be downloaded."""


def _download(
    label: str,
    url: str,
    operation: Callable[[], object],
) -> None:
    print(f"Downloading {label} from {url}...", flush=True)
    try:
        operation()
    except Exception as error:
        reason = str(error).strip()
        if reason:
            reason = f"{type(error).__name__}: {reason}"
        else:
            reason = type(error).__name__
        message = f"Failed to download {label} from {url}: {reason}"
        print(message, file=sys.stderr, flush=True)
        raise ModelDownloadError(message) from error
    print(f"Downloaded {label}.", flush=True)


def _ensure_hugging_face_file(
    *,
    label: str,
    repository: str,
    download_url: str,
    filename: str,
    target_dir: Path,
) -> None:
    if (target_dir / filename).is_file():
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    _download(
        f"{label} file {filename!r}",
        download_url,
        partial(
            hf_hub_download,
            repo_id=repository,
            filename=filename,
            local_dir=target_dir,
        ),
    )


def _ensure_hugging_face_files(
    *,
    label: str,
    repository: str,
    download_url: str,
    files: tuple[str, ...],
    target_dir: Path,
) -> None:
    for filename in files:
        _ensure_hugging_face_file(
            label=label,
            repository=repository,
            download_url=f"{download_url}/{filename}",
            filename=filename,
            target_dir=target_dir,
        )


def _ensure_direct_file(*, label: str, url: str, target_path: Path) -> None:
    if target_path.is_file():
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_name(f"{target_path.name}.part")

    def download_file() -> None:
        try:
            with urlopen(url) as response, temporary_path.open("wb") as output:
                copyfileobj(response, output)
            temporary_path.replace(target_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    _download(label, url, download_file)


def ensure_models_available(
    settings: ApplicationSettings | None = None,
) -> None:
    """Download every required model artifact that is not available locally."""

    current_settings = settings or ApplicationSettings.get_settings()

    _ensure_hugging_face_files(
        label="translation model",
        repository=current_settings.translation_model_repository,
        download_url=current_settings.translation_model_download_url,
        files=current_settings.translation_model_files,
        target_dir=current_settings.translation_model,
    )
    _ensure_direct_file(
        label="language detection model",
        url=current_settings.language_detector_download_url,
        target_path=current_settings.language_detector,
    )
    _ensure_hugging_face_files(
        label="intent detection model",
        repository=current_settings.intent_detection_model_repository,
        download_url=current_settings.intent_detection_model_download_url,
        files=current_settings.intent_detection_model_files,
        target_dir=current_settings.intent_detection_model,
    )
    _ensure_hugging_face_file(
        label="information extraction model",
        repository=current_settings.information_extraction_model_repository,
        download_url=current_settings.information_extraction_model_download_url,
        filename=current_settings.information_extraction_model_filename,
        target_dir=current_settings.information_extraction_model_data_folder,
    )
