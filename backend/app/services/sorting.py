"""Chronological ordering, as a pure function over NormalizedEvent."""

from __future__ import annotations

from datetime import time as Time

from app.services.normalizer import NormalizedEvent

_UNTIMED_SORTS_LAST = Time(23, 59, 59)


def sort_events(events: list[NormalizedEvent]) -> list[NormalizedEvent]:
    """Sort by date, then start time. Events with no time sort last within their day."""
    return sorted(
        events,
        key=lambda event: (event.date, event.start_time or _UNTIMED_SORTS_LAST, event.venue.lower()),
    )
