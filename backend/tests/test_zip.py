"""ZIP archive creation from a list of PNG paths."""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.rendering.zipper import create_zip


def test_create_zip_contains_all_files(tmp_path: Path) -> None:
    png_1 = tmp_path / "01-cover.png"
    png_2 = tmp_path / "02-jeudi.png"
    png_1.write_bytes(b"fake-png-1")
    png_2.write_bytes(b"fake-png-2")

    zip_path = tmp_path / "out" / "nuit-blanche-semaine-29.zip"
    result = create_zip([png_1, png_2], zip_path)

    assert result == zip_path
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        assert names == ["01-cover.png", "02-jeudi.png"]
        assert archive.read("01-cover.png") == b"fake-png-1"
