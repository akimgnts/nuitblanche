"""Input schema: the generic JSON contract the Python engine receives.

This is intentionally decoupled from Google Sheets. Whatever reads the
Sheet (Apps Script today, something else tomorrow) is responsible for
producing this shape. See docs/GOOGLE_SHEET_MAPPING.md for the column
mapping used to build it.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import time as Time

from pydantic import BaseModel, Field, field_validator

MAX_TITLE_LENGTH = 300
MAX_EVENTS_PER_REQUEST = 500


class EventIn(BaseModel):
    """A single event row, as received from the Google Sheet export."""

    external_id: str = Field(..., min_length=1, max_length=200)
    date: Date
    start_time: Time | None = None
    end_time: Time | None = None
    venue: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LENGTH)
    artist: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    price: str | None = Field(default=None, max_length=100)
    poster_url: str | None = Field(default=None, max_length=2000)
    featured: bool = False

    @field_validator("external_id", "venue", "category", "title", mode="before")
    @classmethod
    def _strip_required(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("artist", "description", "price", "poster_url", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class WeekRequest(BaseModel):
    """The full payload for one carousel generation."""

    city: str = Field(..., min_length=1, max_length=120)
    week_number: int = Field(..., ge=1, le=53)
    start_date: Date
    end_date: Date
    events: list[EventIn] = Field(..., max_length=MAX_EVENTS_PER_REQUEST)

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, end_date: Date, info: object) -> Date:
        start_date = info.data.get("start_date") if hasattr(info, "data") else None
        if start_date is not None and end_date < start_date:
            raise ValueError("end_date must not be before start_date")
        return end_date
