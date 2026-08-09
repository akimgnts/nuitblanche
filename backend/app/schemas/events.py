"""Schemas for the Apps Script payload and the internal generation request."""

from __future__ import annotations

from datetime import date as Date
from datetime import time as Time

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_TITLE_LENGTH = 300
MAX_EVENTS_PER_REQUEST = 500


class EventIn(BaseModel):
    """Single event as sent by Apps Script."""

    id: str = Field(..., min_length=1, max_length=200)
    date: Date
    date_label: str = Field(..., alias="dateLabel", min_length=1, max_length=120)
    venue: str = Field(..., min_length=1, max_length=200)
    venue_id: str | None = Field(default=None, alias="venueId", max_length=50)
    type: str = Field(..., min_length=1, max_length=100)
    event_name: str = Field(..., alias="eventName", min_length=1, max_length=MAX_TITLE_LENGTH)
    artists: str | None = Field(default=None, max_length=500)
    start_time: Time | None = Field(default=None, alias="startTime")
    end_time: Time | None = Field(default=None, alias="endTime")
    price: str | None = Field(default=None, max_length=100)
    media_id: str | None = Field(default=None, alias="mediaId", max_length=200)
    visual_url: str | None = Field(default=None, alias="visualUrl", max_length=2000)
    featured: bool = False
    status: str | None = Field(default=None, max_length=50)
    source_url: str | None = Field(default=None, alias="sourceUrl", max_length=2000)

    @field_validator("id", "date_label", "venue", "type", "event_name", mode="before")
    @classmethod
    def _strip_required(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("price", mode="before")
    @classmethod
    def _normalize_price(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return None if value.strip() == "" else value
        return str(value)

    @field_validator("artists", "media_id", "visual_url", "source_url", "venue_id", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class Week(BaseModel):
    """Week descriptor as sent by Apps Script."""

    label: str = Field(..., min_length=1, max_length=200)
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
    """Generation options preserved from Apps Script payload."""

    statuses: list[str] = Field(default_factory=list)
    sort: list[str] = Field(default_factory=list)


class WeekRequest(BaseModel):
    """Exact Apps Script payload accepted by the FastAPI route."""

    model_config = ConfigDict(extra="forbid")

    project: str = Field(..., min_length=1, max_length=100)
    template: str = Field(..., min_length=1, max_length=100)
    week: Week
    options: GenerationOptions = Field(default_factory=GenerationOptions)
    events: list[EventIn] = Field(..., max_length=MAX_EVENTS_PER_REQUEST)


class GenerationRequest(BaseModel):
    """Internal request consumed by the generation engine."""

    project: str = Field(..., min_length=1, max_length=100)
    template: str = Field(..., min_length=1, max_length=100)
    city: str = Field(..., min_length=1, max_length=120)
    week_number: int = Field(..., ge=1, le=53)
    week: Week
    options: GenerationOptions = Field(default_factory=GenerationOptions)
    events: list[EventIn] = Field(..., max_length=MAX_EVENTS_PER_REQUEST)
    instagram_handle: str | None = Field(default=None, max_length=100)
