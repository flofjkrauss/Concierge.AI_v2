"""Download the local model artifacts required by ``M2M100Translator``."""

from pathlib import Path
from shutil import copyfileobj
from urllib.request import urlopen

from huggingface_hub import hf_hub_download

_MODEL_DATA_DIR = Path(__file__).resolve().parent / "model_data"
#block for m2m100_418
"""
_TRANSLATION_MODEL_DIR = _MODEL_DATA_DIR / "m2m100_418M"
_TRANSLATION_REPOSITORY = "facebook/m2m100_418M"
_TRANSLATION_FILES = (
    "config.json",
    "generation_config.json",
    "pytorch_model.bin",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "vocab.json",
)
"""

#nllb-200-distilled-600M
_TRANSLATION_MODEL_DIR = _MODEL_DATA_DIR / "nllb-200-distilled-600M"
_TRANSLATION_REPOSITORY = "facebook/nllb-200-distilled-600M"

_TRANSLATION_FILES = (
    "config.json",
    "generation_config.json",
    "pytorch_model.bin",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
)
_LANGUAGE_MODEL_URL = (
    "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
)
_LANGUAGE_MODEL_PATH = _MODEL_DATA_DIR / "lid.176.bin"


def download_models() -> None:
    """Download only the model files used during local inference."""

    _TRANSLATION_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for filename in _TRANSLATION_FILES:
        hf_hub_download(
            repo_id=_TRANSLATION_REPOSITORY,
            filename=filename,
            local_dir=_TRANSLATION_MODEL_DIR,
        )

    if not _LANGUAGE_MODEL_PATH.exists():
        temporary_path = _LANGUAGE_MODEL_PATH.with_suffix(".bin.part")
        with (
            urlopen(_LANGUAGE_MODEL_URL) as response,
            temporary_path.open("wb") as output,
        ):
            copyfileobj(response, output)
        temporary_path.replace(_LANGUAGE_MODEL_PATH)


if __name__ == "__main__":
    download_models()
