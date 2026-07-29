"""Bundle generated PNG slides into a single ZIP archive."""

from __future__ import annotations

import zipfile
from pathlib import Path


def create_zip(png_paths: list[Path], zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for png_path in png_paths:
            archive.write(png_path, arcname=png_path.name)
    return zip_path
