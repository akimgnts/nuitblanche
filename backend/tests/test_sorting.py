"""Chronological ordering of normalized events."""

from __future__ import annotations

from app.schemas.events import EventIn
from app.services.normalizer import normalize_events
from app.services.sorting import sort_events


def _event(event_id: str, date: str, start_time: str | None, venue: str = "Venue") -> EventIn:
    return EventIn.model_validate(
        {
            "id": event_id,
            "date": date,
            "dateLabel": "Jeudi 16 juillet",
            "startTime": start_time,
            "venue": venue,
            "type": "Concert",
            "eventName": f"Title {event_id}",
        }
    )


def test_sort_events_by_date_then_time() -> None:
    events = normalize_events(
        [
            _event("late", "2026-07-16", "22:00"),
            _event("early", "2026-07-16", "18:00"),
            _event("next-day", "2026-07-17", "10:00"),
        ]
    )
    sorted_events = sort_events(events)
    assert [event.external_id for event in sorted_events] == ["early", "late", "next-day"]


def test_events_without_time_sort_last_within_their_day() -> None:
    events = normalize_events(
        [
            _event("no-time", "2026-07-16", None),
            _event("morning", "2026-07-16", "09:00"),
        ]
    )
    sorted_events = sort_events(events)
    assert [event.external_id for event in sorted_events] == ["morning", "no-time"]


def test_sort_is_stable_by_venue_for_identical_times() -> None:
    events = normalize_events(
        [
            _event("z-venue", "2026-07-16", "20:00", venue="Zoo"),
            _event("a-venue", "2026-07-16", "20:00", venue="Auditorium"),
        ]
    )
    sorted_events = sort_events(events)
    assert [event.external_id for event in sorted_events] == ["a-venue", "z-venue"]
