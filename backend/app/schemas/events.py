"""Input schema: the generic JSON contract the Python engine receives.

This is intentionally decoupled from Google Sheets. Whatever reads the
Sheet (Apps Script today, something else tomorrow) is responsible for
producing this shape. See docs/GOOGLE_SHEET_MAPPING.md for the column
mapping used to build it.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import time as Time

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_TITLE_LENGTH = 300
MAX_EVENTS_PER_REQUEST = 500


class EventIn(BaseModel):
    """A single event, matching the Google Sheet contract structure."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., min_length=1, max_length=200, description="Event ID from sheet (EVT-0001, etc)")
    date: Date
    venue: str = Field(..., min_length=1, max_length=200)
    venue_id: str | None = Field(default=None, alias="venueId", max_length=50, description="Location identifier (CAI, COS, etc)")
    type: str = Field(..., min_length=1, max_length=100, description="Event category/type")
    event_name: str = Field(..., alias="eventName", min_length=1, max_length=MAX_TITLE_LENGTH)
    artists: str | None = Field(default=None, max_length=500, description="Artists, DJ, or performers")
    start_time: Time | None = Field(default=None, alias="startTime")
    end_time: Time | None = Field(default=None, alias="endTime")
    price: str | None = Field(default=None, max_length=100)
    visual_url: str | None = Field(default=None, alias="visualUrl", max_length=2000, description="Poster image URL from Drive")
    featured: bool = False
    status: str | None = Field(default="Validé", max_length=50, description="Event status from sheet")
    source_url: str | None = Field(default=None, alias="sourceUrl", max_length=2000, description="Instagram, ticketing, or source URL")

    @field_validator("id", "venue", "type", "event_name", mode="before")
    @classmethod
    def _strip_required(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("artists", "price", "visual_url", "source_url", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class Week(BaseModel):
    """Week descriptor from the Google Sheet calendar."""

    model_config = ConfigDict(populate_by_name=True)

    label: str = Field(..., description="Human-readable label (Semaine 32 – du 03/08/2026 au 09/08/2026)")
    start_date: Date = Field(..., alias="startDate")
    end_date: Date = Field(..., alias="endDate")

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, end_date: Date, info: object) -> Date:
        start_date = info.data.get("start_date") if hasattr(info, "data") else None
        if start_date is not None and end_date < start_date:
            raise ValueError("end_date must not be before start_date")
        return end_date


class GenerationOptions(BaseModel):
    """Options for carousel generation."""

    model_config = ConfigDict(populate_by_name=True)

    statuses: list[str] = Field(default=["Validé"], description="Event statuses to include")
    featured_first: bool = Field(default=True, alias="featuredFirst", description="Featured events appear first on slides")


class WeekRequest(BaseModel):
    """The full payload for carousel generation from Google Sheets."""

    project: str = Field(default="nuit-blanche", max_length=100)
    template: str = Field(default="nuit-blanche", max_length=100)
    city: str = Field(..., min_length=1, max_length=120)
    week_number: int = Field(..., ge=1, le=53)
    week: Week
    options: GenerationOptions = Field(default_factory=GenerationOptions)
    events: list[EventIn] = Field(..., max_length=MAX_EVENTS_PER_REQUEST)
    instagram_handle: str | None = Field(
        default=None, max_length=100, description="Shown on the closing slide; defaults to @nuitblanche.<city>."
    )
