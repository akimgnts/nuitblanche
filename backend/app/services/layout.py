"""Density estimation, slide pagination and template selection.

All pure functions: given the same events, they always produce the
same slide plan. No I/O, no rendering here.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import date as Date

from app.services.normalizer import NormalizedEvent

MAX_EVENTS_PER_SLIDE = 8

Template = str  # "spacious" | "standard" | "compact"


def estimate_density(event_count: int) -> Template:
    """Day slides use one uniform dense layout, whatever the event count."""
    del event_count
    return "compact"


@dataclass(frozen=True)
class DaySlide:
    """One slide's worth of events for a given day, possibly one of several pages."""

    day: Date
    events: list[NormalizedEvent]
    template: Template
    page_number: int
    page_count: int

    @property
    def has_featured(self) -> bool:
        return any(event.featured for event in self.events)


def paginate_day(day: Date, events: list[NormalizedEvent]) -> list[DaySlide]:
    """
    Split one day's events into uniform slides of up to 8 events.
    """
    if not events:
        return []

    slides_data = [events[i : i + MAX_EVENTS_PER_SLIDE] for i in range(0, len(events), MAX_EVENTS_PER_SLIDE)]

    page_count = len(slides_data)
    return [
        DaySlide(
            day=day,
            events=slide_events,
            template=estimate_density(len(slide_events)),
            page_number=page_number,
            page_count=page_count,
        )
        for page_number, slide_events in enumerate(slides_data, start=1)
    ]


def build_day_slides(grouped_events: OrderedDict[Date, list[NormalizedEvent]]) -> list[DaySlide]:
    """Turn a day -> events mapping (in day order) into an ordered list of slides."""
    slides: list[DaySlide] = []
    for day, events in grouped_events.items():
        slides.extend(paginate_day(day, events))
    return slides
