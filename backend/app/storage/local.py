"""Local filesystem storage — what the MVP actually uses."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.storage.base import StorageProvider, StoredGeneration


class LocalStorageProvider(StorageProvider):
    """Copies generated files into generated/<generation_id>/."""

    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir

    def store(
        self,
        *,
        generation_id: str,
        city: str,
        week_number: int,
        year: int,
        png_paths: list[Path],
        manifest_path: Path,
        zip_path: Path,
    ) -> StoredGeneration:
        del city, week_number, year
        target_dir = self._root_dir / generation_id
        target_dir.mkdir(parents=True, exist_ok=True)

        stored_slide_paths: list[Path] = []
        for source in png_paths:
            destination = target_dir / source.name
            shutil.copy2(source, destination)
            stored_slide_paths.append(destination)

        stored_manifest_path = target_dir / manifest_path.name
        shutil.copy2(manifest_path, stored_manifest_path)

        stored_zip_path = target_dir / zip_path.name
        shutil.copy2(zip_path, stored_zip_path)

        return StoredGeneration(
            location=str(target_dir),
            output_dir=target_dir,
            slide_paths=stored_slide_paths,
            manifest_path=stored_manifest_path,
            zip_path=stored_zip_path,
        )
