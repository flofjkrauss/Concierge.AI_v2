"""Tests for Streamlit presentation helpers."""

from pathlib import Path

from client.components.views import _room_image_path


def test_room_image_prefers_matching_resource_image(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    resource_dir = tmp_path / "res"
    asset_dir.mkdir()
    resource_dir.mkdir()
    fallback = asset_dir / "room-double.svg"
    preferred = resource_dir / "room-double.png"
    fallback.touch()
    preferred.touch()

    assert _room_image_path(asset_dir, "double") == preferred


def test_room_image_uses_svg_when_resource_image_is_missing(
    tmp_path: Path,
) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    fallback = asset_dir / "room-family.svg"
    fallback.touch()

    assert _room_image_path(asset_dir, "family") == fallback


def test_unknown_room_category_uses_deluxe_svg_fallback(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()

    assert _room_image_path(asset_dir, "penthouse") == (asset_dir / "room-deluxe.svg")
