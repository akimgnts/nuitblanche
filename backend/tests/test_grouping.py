"""Grouping normalized events by calendar day."""

from __future__ import annotations

from datetime import date

from app.schemas.events import EventIn
from app.services.grouping import group_by_day
from app.services.normalizer import normalize_events
from app.services.sorting import sort_events


def _event(event_id: str, day: str) -> EventIn:
    return EventIn.model_validate(
        {
            "id": event_id,
            "date": day,
            "venue": "Venue",
            "type": "Concert",
            "event_name": f"Title {event_id}",
        }
    )


def test_group_by_day_preserves_day_order_and_membership() -> None:
    events = normalize_events(
        [
            _event("thu-1", "2026-07-16"),
            _event("fri-1", "2026-07-17"),
            _event("thu-2", "2026-07-16"),
        ]
    )
    grouped = group_by_day(sort_events(events))

    assert list(grouped.keys()) == [date(2026, 7, 16), date(2026, 7, 17)]
    assert [event.external_id for event in grouped[date(2026, 7, 16)]] == ["thu-1", "thu-2"]
    assert [event.external_id for event in grouped[date(2026, 7, 17)]] == ["fri-1"]


def test_group_by_day_on_empty_list() -> None:
    assert group_by_day([]) == {}
