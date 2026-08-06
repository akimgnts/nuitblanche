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

    output_dir: Path
    """Root directory for this generation's stored artifacts."""

    slide_paths: list[Path]
    """Local filesystem paths to the generated PNG slides."""

    manifest_path: Path
    """Local filesystem path to the manifest JSON."""

    zip_path: Path
    """Local filesystem path to the optional ZIP download."""


class StorageProvider(ABC):
    @abstractmethod
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
        """Persist the generated slides + manifest + zip and return where they ended up."""
        raise NotImplementedError
