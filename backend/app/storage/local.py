"""Local filesystem storage — what the MVP actually uses."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.storage.base import StorageProvider, StoredGeneration


class LocalStorageProvider(StorageProvider):
    """Copies generated files into generated/<year>/Semaine <n>/."""

    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir

    def store(
        self,
        *,
        city: str,
        week_number: int,
        year: int,
        png_paths: list[Path],
        zip_path: Path,
    ) -> StoredGeneration:
        target_dir = self._root_dir / str(year) / f"Semaine {week_number}"
        target_dir.mkdir(parents=True, exist_ok=True)

        stored_paths = []
        for source in [*png_paths, zip_path]:
            destination = target_dir / source.name
            shutil.copy2(source, destination)
            stored_paths.append(destination)

        return StoredGeneration(location=str(target_dir), file_paths=stored_paths)
