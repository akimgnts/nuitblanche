"""Storage abstraction: where generated slides end up.

The rendering pipeline never talks to a filesystem or an external API
directly — it hands finished files to a `StorageProvider`. Swapping
`LocalStorageProvider` for `GoogleDriveStorageProvider` later requires
no change to the generation service.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredGeneration:
    """Where a finished generation lives, and how to reach it."""

    location: str
    """Human-meaningful location: a local path, or a Drive folder URL."""

    file_paths: list[Path]
    """Local filesystem paths to the files, used for the download route."""


class StorageProvider(ABC):
    @abstractmethod
    def store(
        self,
        *,
        city: str,
        week_number: int,
        year: int,
        png_paths: list[Path],
        zip_path: Path,
    ) -> StoredGeneration:
        """Persist the generated slides + zip and return where they ended up."""
        raise NotImplementedError
