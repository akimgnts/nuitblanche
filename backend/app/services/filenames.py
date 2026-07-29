"""Deterministic, filesystem-safe names for generated slide files."""

from __future__ import annotations

import re
import unicodedata
from datetime import date as Date

from app.services.layout import DaySlide

_FRENCH_WEEKDAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "slide"


def weekday_name(day: Date) -> str:
    return _FRENCH_WEEKDAYS[day.weekday()]


def cover_filename() -> str:
    return "01-cover.png"


def outro_filename(index: int) -> str:
    return f"{index:02d}-fin.png"


def day_slide_filename(index: int, slide: DaySlide) -> str:
    base = weekday_name(slide.day)
    if slide.page_count > 1:
        return f"{index:02d}-{base}-{slide.page_number}.png"
    return f"{index:02d}-{base}.png"


def zip_filename(week_number: int) -> str:
    return f"nuit-blanche-semaine-{week_number}.zip"
