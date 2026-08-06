"""Shared pytest fixtures.

Sets a valid, test-only API key before `app.main` is imported anywhere,
since Settings() requires NUIT_BLANCHE_API_KEY to be set and refuses to
start otherwise.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("NUIT_BLANCHE_API_KEY", "test-api-key")
os.environ.setdefault("NUIT_BLANCHE_DOWNLOAD_URL_SECRET", "test-download-secret")
os.environ.setdefault("NUIT_BLANCHE_GENERATION_TIMEOUT_SECONDS", "30")

import pytest  # noqa: E402

TEST_API_KEY = os.environ["NUIT_BLANCHE_API_KEY"]

EXAMPLES_PATH = Path(__file__).resolve().parent.parent.parent / "examples" / "events.demo.json"


@pytest.fixture
def minimal_week_payload() -> dict[str, object]:
    return {
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
                "startTime": "20:00",
                "venue": "3 Brasseurs",
                "venueId": "3BR",
                "type": "Concert",
                "eventName": "Concert variétés",
                "artists": "Artiste invité",
            }
        ],
    }
