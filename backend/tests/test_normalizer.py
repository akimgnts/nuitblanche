"""Normalization helpers around poster URL resolution."""

from __future__ import annotations

from app.schemas.events import EventIn
from app.services.normalizer import normalize_event


def _event(**overrides: object) -> EventIn:
    payload = {
        "id": "EVT-0001",
        "date": "2026-07-16",
        "dateLabel": "Jeudi 16 juillet",
        "venue": "3 Brasseurs",
        "type": "Concert",
        "eventName": "Concert variétés",
    }
    payload.update(overrides)
    return EventIn.model_validate(payload)


def test_normalize_event_uses_media_id_when_present() -> None:
    event = _event(mediaId="1AbCdEf")

    normalized = normalize_event(event)

    assert normalized.poster_url == "https://drive.google.com/uc?export=view&id=1AbCdEf"


def test_normalize_event_falls_back_to_visual_url() -> None:
    event = _event(visualUrl="https://example.com/poster.png")

    normalized = normalize_event(event)

    assert normalized.poster_url == "https://example.com/poster.png"


def test_normalize_event_prioritizes_media_id_over_visual_url() -> None:
    event = _event(
        mediaId="1AbCdEf",
        visualUrl="https://example.com/legacy-poster.png",
    )

    normalized = normalize_event(event)

    assert normalized.poster_url == "https://drive.google.com/uc?export=view&id=1AbCdEf"


def test_normalize_event_keeps_missing_poster_behavior() -> None:
    event = _event()

    normalized = normalize_event(event)

    assert normalized.poster_url is None
