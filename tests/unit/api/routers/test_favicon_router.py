from pathlib import Path

from api.routers.favicon import favicon
from configuration.fastapi import FastapiSettings


def test_favicon_returns_configured_icon_file(tmp_path: Path) -> None:
    icon = tmp_path / "favicon.ico"
    icon.write_bytes(b"icon")

    response = favicon(FastapiSettings(favicon_path=icon))

    assert Path(response.path) == icon
    assert response.media_type == "image/vnd.microsoft.icon"
