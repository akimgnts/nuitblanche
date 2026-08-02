"""Shared pytest fixtures.

Sets a valid, test-only API key before `app.main` is imported anywhere,
since Settings() requires NUIT_BLANCHE_API_KEY to be set and refuses to
start otherwise.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("NUIT_BLANCHE_API_KEY", "test-api-key")
os.environ.setdefault("NUIT_BLANCHE_GENERATION_TIMEOUT_SECONDS", "30")

import pytest  # noqa: E402

TEST_API_KEY = os.environ["NUIT_BLANCHE_API_KEY"]

EXAMPLES_PATH = Path(__file__).resolve().parent.parent.parent / "examples" / "events.demo.json"


@pytest.fixture
def minimal_week_payload() -> dict[str, object]:
    return {
        "city": "Le Havre",
        "week_number": 29,
        "week": {
            "label": "Semaine 29 – du 16/07/2026 au 22/07/2026",
            "start_date": "2026-07-16",
            "end_date": "2026-07-22",
        },
        "options": {
            "statuses": ["Validé"],
            "featured_first": True,
        },
        "events": [
            {
                "id": "EVT-0001",
                "date": "2026-07-16",
                "start_time": "20:00",
                "venue": "3 Brasseurs",
                "venue_id": "3BR",
                "type": "Concert",
                "event_name": "Concert variétés",
                "artists": "Artiste invité",
            }
        ],
    }
