"""Generation service integration with the real renderer."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.models.generation import GenerationRepository
from app.schemas.events import WeekRequest
from app.services.generation_service import GenerationService
from app.services.payload_adapter import to_generation_request
from app.storage.local import LocalStorageProvider


def test_generation_service_preserves_existing_output_shape(tmp_path: Path) -> None:
    payload = WeekRequest.model_validate(
        {
            "project": "nuit-blanche",
            "template": "nuit-blanche",
            "week": {
                "label": "Semaine 29 – du 16/07/2026 au 22/07/2026",
                "startDate": "2026-07-16",
                "endDate": "2026-07-22",
            },
            "options": {
                "statuses": ["Validé"],
                "sort": ["date", "startTime", "venue"],
            },
            "events": [
                {
                    "id": "EVT-0001",
                    "date": "2026-07-16",
                    "dateLabel": "Jeudi 16 juillet",
                    "venue": "3 Brasseurs",
                    "venueId": "3BR",
                    "type": "Concert",
                    "eventName": "Concert variétés",
                    "artists": "Artiste invité",
                    "startTime": "20:00",
                }
            ],
        }
    )
    settings = Settings(api_key="test-key", generated_dir=tmp_path)
    request = to_generation_request(payload, settings)
    service = GenerationService(
        settings=settings,
        storage=LocalStorageProvider(root_dir=tmp_path),
        repository=GenerationRepository(),
    )

    record = service.generate(request)

    assert record.slide_count == 3
    assert record.files == ["01-cover.png", "02-jeudi.png", "03-fin.png"]
    assert record.output_dir.name == record.generation_id
    assert [path.name for path in record.slide_paths] == record.files
    assert record.manifest_path.exists()
    assert record.zip_path.exists()
    manifest = json.loads(record.manifest_path.read_text(encoding="utf-8"))
    assert manifest == {
        "generation_id": record.generation_id,
        "week": "Semaine 29 – du 16/07/2026 au 22/07/2026",
        "slide_count": 3,
        "slides": [
            {"index": 1, "filename": "01-cover.png"},
            {"index": 2, "filename": "02-jeudi.png"},
            {"index": 3, "filename": "03-fin.png"},
        ],
    }
