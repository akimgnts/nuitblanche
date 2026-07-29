"""Orchestrates one full carousel generation.

validate (done upstream by Pydantic) -> normalize -> sort -> group ->
paginate -> render -> screenshot -> post-process -> zip -> store.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import date as Date
from datetime import time as Time
from pathlib import Path

from app.core.config import Settings
from app.models.generation import GenerationRecord, GenerationRepository
from app.rendering.postprocess import finalize_png
from app.rendering.renderer import render_slide
from app.rendering.screenshot import ScreenshotRenderer
from app.rendering.zipper import create_zip
from app.schemas.events import WeekRequest
from app.services.filenames import (
    cover_filename,
    day_slide_filename,
    outro_filename,
    weekday_name,
    zip_filename,
)
from app.services.grouping import group_by_day
from app.services.layout import DaySlide, build_day_slides
from app.services.normalizer import NormalizedEvent, normalize_events
from app.services.sorting import sort_events
from app.storage.base import StorageProvider

_FRENCH_MONTHS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def _format_date(day: Date) -> str:
    return f"{day.day} {_FRENCH_MONTHS[day.month - 1]}"


def _format_period_label(start_date: Date, end_date: Date) -> str:
    return f"Du {_format_date(start_date)} au {_format_date(end_date)} {end_date.year}"


def _format_hm(value: Time) -> str:
    if value.minute == 0:
        return f"{value.hour}h"
    return f"{value.hour}h{value.minute:02d}"


def _format_time_label(event: NormalizedEvent) -> str | None:
    if event.start_time is None:
        return None
    label = _format_hm(event.start_time)
    if event.end_time is not None:
        label = f"{label} – {_format_hm(event.end_time)}"
    return label


def _event_to_context(event: NormalizedEvent) -> dict[str, object]:
    return {
        "title_display": event.title_display,
        "artist_display": event.artist_display,
        "description_display": event.description_display,
        "venue": event.venue,
        "category": event.category,
        "price_display": event.price_display,
        "poster_src": event.poster_src,
        "featured": event.featured,
        "start_time_label": _format_time_label(event),
    }


def _render_cover(request: WeekRequest) -> str:
    return render_slide(
        "cover.html",
        {
            "slide_type": "cover",
            "week_number": request.week_number,
            "city": request.city,
            "period_label": _format_period_label(request.start_date, request.end_date),
            "headline": "Le programme culturel de la semaine",
        },
    )


def _render_day(request: WeekRequest, slide: DaySlide) -> str:
    return render_slide(
        "day.html",
        {
            "slide_type": "day",
            "week_number": request.week_number,
            "city": request.city,
            "day_name": weekday_name(slide.day),
            "day_date_label": _format_date(slide.day),
            "template": slide.template,
            "page_number": slide.page_number,
            "page_count": slide.page_count,
            "events": [_event_to_context(event) for event in slide.events],
        },
    )


def _render_outro() -> str:
    return render_slide(
        "outro.html",
        {
            "slide_type": "outro",
            "closing_message": "C'était le programme de la semaine.",
            "call_to_action": "Abonnez-vous pour ne rien manquer du prochain épisode.",
        },
    )


class GenerationService:
    """Stateless orchestrator: all state lives in the repository/storage it's given."""

    def __init__(
        self,
        settings: Settings,
        storage: StorageProvider,
        repository: GenerationRepository,
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._repository = repository

    def generate(self, request: WeekRequest) -> GenerationRecord:
        generation_id = str(uuid.uuid4())
        warnings: list[str] = []

        normalized = normalize_events(request.events)
        sorted_events = sort_events(normalized)
        grouped = group_by_day(sorted_events)
        day_slides = build_day_slides(grouped)

        if not day_slides:
            warnings.append("Aucun événement fourni pour cette semaine : seules la couverture et la fin ont été générées.")

        total_slides = 1 + len(day_slides) + 1  # cover + programme + fin
        width, height = self._settings.slide_width, self._settings.slide_height

        with tempfile.TemporaryDirectory(prefix=f"nuit-blanche-{generation_id}-") as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            png_paths: list[Path] = []

            with ScreenshotRenderer(width, height, self._settings.chromium_executable_path) as screenshot:
                cover_path = tmp_dir / cover_filename()
                screenshot.capture(_render_cover(request), cover_path)
                finalize_png(cover_path, width, height)
                png_paths.append(cover_path)

                for index, slide in enumerate(day_slides, start=2):
                    slide_path = tmp_dir / day_slide_filename(index, slide)
                    screenshot.capture(_render_day(request, slide), slide_path)
                    finalize_png(slide_path, width, height)
                    png_paths.append(slide_path)

                outro_path = tmp_dir / outro_filename(total_slides)
                screenshot.capture(_render_outro(), outro_path)
                finalize_png(outro_path, width, height)
                png_paths.append(outro_path)

            zip_path = tmp_dir / zip_filename(request.week_number)
            create_zip(png_paths, zip_path)

            stored = self._storage.store(
                city=request.city,
                week_number=request.week_number,
                year=request.start_date.year,
                png_paths=png_paths,
                zip_path=zip_path,
            )

        stored_zip_path = next(path for path in stored.file_paths if path.name == zip_path.name)
        stored_png_paths = [path for path in stored.file_paths if path.name != zip_path.name]

        record = GenerationRecord(
            generation_id=generation_id,
            city=request.city,
            week_number=request.week_number,
            status="completed",
            slide_count=len(png_paths),
            files=[path.name for path in stored_png_paths],
            output_dir=stored_zip_path.parent,
            zip_path=stored_zip_path,
            warnings=warnings,
        )
        self._repository.add(record)
        return record
