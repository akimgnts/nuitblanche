"""Deterministic slide and archive file names."""

from __future__ import annotations

from datetime import date

from app.services.filenames import (
    cover_filename,
    day_slide_filename,
    outro_filename,
    slugify,
    weekday_name,
    zip_filename,
)
from app.services.layout import DaySlide


def test_cover_and_outro_filenames() -> None:
    assert cover_filename() == "01-cover.png"
    assert outro_filename(6) == "06-fin.png"


def test_weekday_name_in_french() -> None:
    assert weekday_name(date(2026, 7, 16)) == "jeudi"
    assert weekday_name(date(2026, 7, 20)) == "lundi"


def test_day_slide_filename_without_pagination() -> None:
    slide = DaySlide(day=date(2026, 7, 16), events=[], template="spacious", page_number=1, page_count=1)
    assert day_slide_filename(2, slide) == "02-jeudi.png"


def test_day_slide_filename_with_pagination() -> None:
    slide = DaySlide(day=date(2026, 7, 17), events=[], template="compact", page_number=2, page_count=2)
    assert day_slide_filename(4, slide) == "04-vendredi-2.png"


def test_zip_filename() -> None:
    assert zip_filename(29) == "nuit-blanche-semaine-29.zip"


def test_slugify_handles_accents_and_spaces() -> None:
    assert slugify("Café de la Gare") == "cafe-de-la-gare"
    assert slugify("   ") == "slide"
