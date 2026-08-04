"""Generate the demo carousel locally, with no Google Sheet and no running API server.

Usage (from the backend/ directory, with the venv active):
    python -m scripts.generate_demo
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# This script calls GenerationService directly and never goes through the
# HTTP layer, so the X-API-Key check never runs. Settings still requires a
# value to be set, so default to a harmless local one if the caller hasn't
# already exported a real key.
os.environ.setdefault("NUIT_BLANCHE_API_KEY", "demo-local-key")

from app.core.config import get_settings  # noqa: E402
from app.models.generation import GenerationRepository  # noqa: E402
from app.schemas.events import WeekRequest  # noqa: E402
from app.services.generation_service import GenerationService  # noqa: E402
from app.services.payload_adapter import to_generation_request  # noqa: E402
from app.storage.local import LocalStorageProvider  # noqa: E402

EXAMPLES_PATH = Path(__file__).resolve().parent.parent.parent / "examples" / "events.demo.json"


def main() -> int:
    if not EXAMPLES_PATH.exists():
        print(f"Demo dataset not found at {EXAMPLES_PATH}", file=sys.stderr)
        return 1

    raw = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    payload = WeekRequest.model_validate(raw)

    settings = get_settings()
    request = to_generation_request(payload, settings)
    storage = LocalStorageProvider(root_dir=settings.generated_dir)
    repository = GenerationRepository()
    service = GenerationService(settings=settings, storage=storage, repository=repository)

    print(f"Génération du carrousel de démonstration pour {request.city}, semaine {request.week_number}...")
    record = service.generate(request)

    print(f"OK — {record.slide_count} slides générées dans {record.output_dir}")
    for filename in record.files:
        print(f"  - {filename}")
    print(f"  - {record.zip_path.name}")

    if record.warnings:
        print("Avertissements :")
        for warning in record.warnings:
            print(f"  - {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
