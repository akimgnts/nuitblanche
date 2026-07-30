"""Normalize validated input events into the internal representation.

Sorting, grouping and layout all operate on `NormalizedEvent`, never on
the raw `EventIn`, so display-only shortcuts (truncated titles,
placeholder posters) never leak back into the source data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from datetime import time as Time

from app.schemas.events import EventIn
from app.services.text_utils import placeholder_color, truncate_text

TITLE_DISPLAY_MAX_LENGTH = 60
ARTIST_DISPLAY_MAX_LENGTH = 50
DESCRIPTION_DISPLAY_MAX_LENGTH = 140
POSTER_LABEL_MAX_LENGTH = 34
NO_PRICE_LABEL = "Tarif non communiqué"


@dataclass(frozen=True)
class NormalizedEvent:
    external_id: str
    date: Date
    start_time: Time | None
    end_time: Time | None
    venue: str
    category: str
    title: str
    title_display: str
    artist: str | None
    artist_display: str | None
    description: str | None
    description_display: str | None
    price_display: str
    poster_url: str | None
    placeholder_color: str
    poster_label: str
    featured: bool


def normalize_event(event: EventIn) -> NormalizedEvent:
    return NormalizedEvent(
        external_id=event.external_id,
        date=event.date,
        start_time=event.start_time,
        end_time=event.end_time,
        venue=event.venue,
        category=event.category,
        title=event.title,
        title_display=truncate_text(event.title, TITLE_DISPLAY_MAX_LENGTH),
        artist=event.artist,
        artist_display=(truncate_text(event.artist, ARTIST_DISPLAY_MAX_LENGTH) if event.artist else None),
        description=event.description,
        description_display=(
            truncate_text(event.description, DESCRIPTION_DISPLAY_MAX_LENGTH) if event.description else None
        ),
        price_display=event.price.strip() if event.price and event.price.strip() else NO_PRICE_LABEL,
        poster_url=event.poster_url,
        placeholder_color=placeholder_color(event.category),
        poster_label=truncate_text(event.title, POSTER_LABEL_MAX_LENGTH),
        featured=event.featured,
    )


def normalize_events(events: list[EventIn]) -> list[NormalizedEvent]:
    return [normalize_event(event) for event in events]
