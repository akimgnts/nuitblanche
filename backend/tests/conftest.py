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
        "start_date": "2026-07-16",
        "end_date": "2026-07-22",
        "events": [
            {
                "external_id": "event-001",
                "date": "2026-07-16",
                "start_time": "20:00",
                "venue": "3 Brasseurs",
                "category": "Concert",
                "title": "Concert variétés",
                "artist": "Artiste invité",
            }
        ],
    }
