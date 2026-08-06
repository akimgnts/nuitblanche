"""Orchestrates one full carousel generation.

validate (done upstream by Pydantic) -> normalize -> sort -> group ->
paginate -> render -> screenshot -> post-process -> zip -> store.
"""

from __future__ import annotations

import json
import re
import tempfile
import unicodedata
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
from app.schemas.events import GenerationRequest
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

MAX_COVER_TAGS = 4
MANIFEST_FILENAME = "manifest.json"


def _format_day_month(day: Date) -> str:
    return f"{day.day} {_FRENCH_MONTHS[day.month - 1]}"


def _format_full_date(day: Date) -> str:
    return f"{_format_day_month(day)} {day.year}"


def _format_period_label(start_date: Date, end_date: Date) -> str:
    if start_date.month == end_date.month and start_date.year == end_date.year:
        return f"Du {start_date.day} au {end_date.day} {_FRENCH_MONTHS[end_date.month - 1]} {end_date.year}"
    return f"Du {_format_day_month(start_date)} au {_format_full_date(end_date)}"


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


def _category_tags(events: list[NormalizedEvent], limit: int = MAX_COVER_TAGS) -> list[str]:
    """Unique categories in order of first appearance, capped for the cover's tag row."""
    seen: dict[str, None] = {}
    for event in events:
        seen.setdefault(event.category, None)
    return list(seen.keys())[:limit]


def _default_instagram_handle(city: str) -> str:
    normalized = unicodedata.normalize("NFKD", city).encode("ascii", "ignore").decode("ascii")
    compact = re.sub(r"[^a-zA-Z0-9]", "", normalized).lower()
    return f"@nuitblanche.{compact}"


def _featured_first(events: list[NormalizedEvent]) -> list[NormalizedEvent]:
    """Display-only reorder: featured events lead the slide, like the reference design."""
    return sorted(events, key=lambda event: not event.featured)


def _event_to_context(event: NormalizedEvent) -> dict[str, object]:
    return {
        "title_display": event.title_display,
        "artist_display": event.artist_display,
        "description_display": event.description_display,
        "venue": event.venue,
        "category": event.category,
        "price_display": event.price_display,
        "poster_url": event.poster_url,
        "placeholder_color": event.placeholder_color,
        "poster_label": event.poster_label,
        "featured": event.featured,
        "start_time_label": _format_time_label(event),
    }


def _render_cover(request: GenerationRequest, normalized_events: list[NormalizedEvent]) -> str:
    return render_slide(
        "cover.html",
        {
            "slide_type": "cover",
            "topbar_variant": "week",
            "week_number": request.week_number,
            "city": request.city,
            "period_label": _format_period_label(request.week.start_date, request.week.end_date),
            "headline_line1": "C'est quoi les plans",
            "headline_line2": "cette semaine",
            "headline_line3": f"à {request.city} ?",
            "category_tags": _category_tags(normalized_events),
        },
    )


def _render_day(request: GenerationRequest, slide: DaySlide, page_label: str) -> str:
    return render_slide(
        "day.html",
        {
            "slide_type": "day",
            "topbar_variant": "section",
            "week_number": request.week_number,
            "city": request.city,
            "day_name": weekday_name(slide.day),
            "day_date_label": _format_full_date(slide.day),
            "template": slide.template,
            "events": [_event_to_context(event) for event in _featured_first(slide.events)],
            "page_label": page_label,
        },
    )


def _render_outro(request: GenerationRequest, page_label: str) -> str:
    return render_slide(
        "outro.html",
        {
            "slide_type": "outro",
            "topbar_variant": "week",
            "week_number": request.week_number,
            "city": request.city,
            "closing_headline": "Trouve ton prochain",
            "closing_headline_accent": f"plan à {request.city}.",
            "closing_text": "Concerts, expositions, spectacles et sorties sélectionnés chaque semaine.",
            "instagram_handle": request.instagram_handle or _default_instagram_handle(request.city),
            "page_label": page_label,
        },
    )


def _write_manifest(
    *,
    generation_id: str,
    week_label: str,
    png_paths: list[Path],
    output_path: Path,
) -> Path:
    manifest = {
        "generation_id": generation_id,
        "week": week_label,
        "slide_count": len(png_paths),
        "slides": [
            {
                "index": index,
                "filename": path.name,
            }
            for index, path in enumerate(png_paths, start=1)
        ],
    }
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


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

    def generate(self, request: GenerationRequest) -> GenerationRecord:
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
                screenshot.capture(_render_cover(request, normalized), cover_path)
                finalize_png(cover_path, width, height)
                png_paths.append(cover_path)

                for index, slide in enumerate(day_slides, start=2):
                    day_name = weekday_name(slide.day)
                    if slide.page_count > 1:
                        page_label = f"{day_name.capitalize()} {slide.page_number}/{slide.page_count}"
                    else:
                        page_label = day_name.capitalize()
                    slide_path = tmp_dir / day_slide_filename(index, slide)
                    screenshot.capture(_render_day(request, slide, page_label), slide_path)
                    finalize_png(slide_path, width, height)
                    png_paths.append(slide_path)

                outro_page_label = f"{total_slides:02d} / {total_slides:02d}"
                outro_path = tmp_dir / outro_filename(total_slides)
                screenshot.capture(_render_outro(request, outro_page_label), outro_path)
                finalize_png(outro_path, width, height)
                png_paths.append(outro_path)

            manifest_path = _write_manifest(
                generation_id=generation_id,
                week_label=request.week.label,
                png_paths=png_paths,
                output_path=tmp_dir / MANIFEST_FILENAME,
            )
            zip_path = tmp_dir / zip_filename(request.week_number)
            create_zip(png_paths, zip_path)

            stored = self._storage.store(
                generation_id=generation_id,
                city=request.city,
                week_number=request.week_number,
                year=request.week.start_date.year,
                png_paths=png_paths,
                manifest_path=manifest_path,
                zip_path=zip_path,
            )

        record = GenerationRecord(
            generation_id=generation_id,
            week=request.week.label,
            city=request.city,
            week_number=request.week_number,
            status="completed",
            slide_count=len(stored.slide_paths),
            files=[path.name for path in stored.slide_paths],
            output_dir=stored.output_dir,
            slide_paths=stored.slide_paths,
            manifest_path=stored.manifest_path,
            zip_path=stored.zip_path,
            warnings=warnings,
        )
        self._repository.add(record)
        return record
