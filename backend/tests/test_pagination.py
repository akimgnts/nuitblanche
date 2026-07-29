"""Slide pagination: a day's events split into slides of at most 8."""

from __future__ import annotations

from collections import OrderedDict
from datetime import date

import pytest

from app.schemas.events import EventIn
from app.services.layout import MAX_EVENTS_PER_SLIDE, build_day_slides, paginate_day
from app.services.normalizer import normalize_events


def _events(count: int, day: str = "2026-07-16") -> list:
    raw = [
        EventIn.model_validate(
            {
                "external_id": f"event-{i}",
                "date": day,
                "venue": "Venue",
                "category": "Concert",
                "title": f"Title {i}",
            }
        )
        for i in range(count)
    ]
    return normalize_events(raw)


def test_paginate_day_with_no_events_returns_no_slides() -> None:
    assert paginate_day(date(2026, 7, 16), []) == []


@pytest.mark.parametrize("count", [1, 4, 6, 8])
def test_paginate_day_fits_in_one_slide_up_to_max(count: int) -> None:
    slides = paginate_day(date(2026, 7, 16), _events(count))
    assert len(slides) == 1
    assert slides[0].page_number == 1
    assert slides[0].page_count == 1
    assert len(slides[0].events) == count


def test_paginate_day_splits_beyond_max_per_slide() -> None:
    slides = paginate_day(date(2026, 7, 16), _events(9))
    assert len(slides) == 2
    assert len(slides[0].events) == MAX_EVENTS_PER_SLIDE
    assert len(slides[1].events) == 1
    assert [slide.page_number for slide in slides] == [1, 2]
    assert all(slide.page_count == 2 for slide in slides)


def test_paginate_day_splits_double_max_evenly() -> None:
    slides = paginate_day(date(2026, 7, 16), _events(16))
    assert [len(slide.events) for slide in slides] == [8, 8]


def test_build_day_slides_across_multiple_days() -> None:
    grouped: OrderedDict = OrderedDict()
    grouped[date(2026, 7, 16)] = _events(2, "2026-07-16")
    grouped[date(2026, 7, 17)] = _events(9, "2026-07-17")

    slides = build_day_slides(grouped)

    assert len(slides) == 3  # 1 slide for day 1, 2 slides (paginated) for day 2
    assert slides[0].day == date(2026, 7, 16)
    assert slides[1].day == date(2026, 7, 17)
    assert slides[2].day == date(2026, 7, 17)
