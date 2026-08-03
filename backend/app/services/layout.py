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

SPACIOUS_MAX = 4
STANDARD_MAX = 6
# 7-8 events => "compact"; beyond MAX_EVENTS_PER_SLIDE, extra events paginate onto new slides.

Template = str  # "spacious" | "standard" | "compact"


def estimate_density(event_count: int) -> Template:
    """Pick a layout density from an event count. Pure function, no rendering."""
    if event_count <= SPACIOUS_MAX:
        return "spacious"
    if event_count <= STANDARD_MAX:
        return "standard"
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
    Split one day's events into slides following Instagram carousel rules:

    - With featured event: 1 featured + up to 6 regular = 7 max per slide
    - Without featured: up to 8 regular per slide
    - Multiple featured events → separate slide for each
    - After distributing featured, group remaining regular events by 8
    """
    if not events:
        return []

    featured = [e for e in events if e.featured]
    regular = [e for e in events if not e.featured]

    slides_data = []

    # Distribute featured events (each gets its own slide + up to 6 regular events)
    for featured_event in featured:
        companion_regular = regular[:6]
        regular = regular[6:]
        slide_events = [featured_event] + companion_regular
        slides_data.append(slide_events)

    # Distribute remaining regular events by chunks of 8
    for i in range(0, len(regular), 8):
        slides_data.append(regular[i : i + 8])

    # If no slides were created (shouldn't happen, but safeguard)
    if not slides_data:
        return []

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
