"""In-process record of a completed generation.

No database for the MVP. This is an in-memory store, which means
records are lost on restart — acceptable since the Apps Script side
persists the download URL it received right after generating.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock


@dataclass(frozen=True)
class GenerationRecord:
    generation_id: str
    week: str
    city: str
    week_number: int
    status: str
    slide_count: int
    files: list[str]
    output_dir: Path
    assets_dir: Path
    slide_paths: list[Path]
    manifest_path: Path
    zip_path: Path
    warnings: list[str] = field(default_factory=list)

    def slide_path_for(self, filename: str) -> Path | None:
        for path in self.slide_paths:
            if path.name == filename:
                return path
        return None


class GenerationRepository:
    """Thread-safe in-memory map of generation_id -> GenerationRecord."""

    def __init__(self) -> None:
        self._records: dict[str, GenerationRecord] = {}
        self._lock = Lock()

    def add(self, record: GenerationRecord) -> None:
        with self._lock:
            self._records[record.generation_id] = record

    def get(self, generation_id: str) -> GenerationRecord | None:
        with self._lock:
            return self._records.get(generation_id)


_repository = GenerationRepository()


def get_repository() -> GenerationRepository:
    return _repository
