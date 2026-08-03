"""Slide pagination: a day's events split into slides of at most 8."""

from __future__ import annotations

from collections import OrderedDict
from datetime import date

import pytest

from app.schemas.events import EventIn
from app.services.layout import MAX_EVENTS_PER_SLIDE, build_day_slides, paginate_day
from app.services.normalizer import normalize_events


def _events(count: int, day: str = "2026-07-16", featured_indices: list[int] | None = None) -> list:
    """Create test events. featured_indices marks which ones should be featured."""
    featured_indices = featured_indices or []
    raw = [
        EventIn.model_validate(
            {
                "id": f"EVT-{i:04d}",
                "date": day,
                "venue": "Venue",
                "type": "Concert",
                "event_name": f"Title {i}",
                "featured": i in featured_indices,
            }
        )
        for i in range(count)
    ]
    return normalize_events(raw)


def test_paginate_day_with_no_events_returns_no_slides() -> None:
    assert paginate_day(date(2026, 7, 16), []) == []


# === Regular events (no featured) ===

@pytest.mark.parametrize("count", [1, 4, 6, 8])
def test_paginate_day_regular_fits_in_one_slide_up_to_max(count: int) -> None:
    """Regular events up to 8 fit in one slide."""
    slides = paginate_day(date(2026, 7, 16), _events(count))
    assert len(slides) == 1
    assert slides[0].page_number == 1
    assert slides[0].page_count == 1
    assert len(slides[0].events) == count
    assert not slides[0].has_featured


def test_paginate_day_regular_9_events_splits() -> None:
    """9 regular events: 8 on slide 1, 1 on slide 2."""
    slides = paginate_day(date(2026, 7, 16), _events(9))
    assert len(slides) == 2
    assert len(slides[0].events) == 8
    assert len(slides[1].events) == 1
    assert [slide.page_number for slide in slides] == [1, 2]
    assert all(slide.page_count == 2 for slide in slides)


def test_paginate_day_regular_16_events_splits_evenly() -> None:
    """16 regular events: 8 + 8."""
    slides = paginate_day(date(2026, 7, 16), _events(16))
    assert len(slides) == 2
    assert [len(slide.events) for slide in slides] == [8, 8]
    assert all(not slide.has_featured for slide in slides)


# === Featured events ===

def test_paginate_day_one_featured_only() -> None:
    """1 featured event alone on a slide."""
    slides = paginate_day(date(2026, 7, 16), _events(1, featured_indices=[0]))
    assert len(slides) == 1
    assert slides[0].has_featured
    assert len(slides[0].events) == 1


def test_paginate_day_one_featured_plus_6_regular() -> None:
    """1 featured + 6 regular = 7 events, 1 slide."""
    slides = paginate_day(date(2026, 7, 16), _events(7, featured_indices=[0]))
    assert len(slides) == 1
    assert len(slides[0].events) == 7
    assert slides[0].has_featured
    # Featured should be first in the slide
    assert slides[0].events[0].featured


def test_paginate_day_one_featured_plus_7_regular_creates_overflow() -> None:
    """1 featured + 7 regular: featured + 6 on slide 1, 1 regular on slide 2."""
    slides = paginate_day(date(2026, 7, 16), _events(8, featured_indices=[0]))
    assert len(slides) == 2
    # Slide 1: featured + 6 regular
    assert len(slides[0].events) == 7
    assert slides[0].has_featured
    # Slide 2: remaining regular events
    assert len(slides[1].events) == 1
    assert not slides[1].has_featured


def test_paginate_day_multiple_featured_same_day() -> None:
    """Multiple featured events get separate slides."""
    # 2 featured + 12 regular
    slides = paginate_day(date(2026, 7, 16), _events(14, featured_indices=[0, 7]))
    # Slide 1: featured[0] + 6 regular
    # Slide 2: featured[1] + 6 regular
    # But order might change, so check by counting slides with featured
    featured_slides = [s for s in slides if s.has_featured]
    assert len(featured_slides) == 2
    # Each featured gets its own slide
    for slide in featured_slides:
        assert sum(1 for e in slide.events if e.featured) == 1


def test_paginate_day_featured_plus_overflow() -> None:
    """1 featured + 13 regular: featured + 6 on slide 1, 8 on slide 2, 1 on slide 3."""
    slides = paginate_day(date(2026, 7, 16), _events(14, featured_indices=[0]))
    assert len(slides) == 3
    # Slide 1: featured + 6 regular = 7
    assert len(slides[0].events) == 7
    assert slides[0].has_featured
    # Slide 2: 8 regular
    assert len(slides[1].events) == 8
    assert not slides[1].has_featured
    # Slide 3: 1 regular
    assert len(slides[2].events) == 1
    assert not slides[2].has_featured


def test_paginate_day_no_slide_exceeds_8_events_without_featured() -> None:
    """Without featured, no slide should exceed 8 events."""
    for count in [8, 9, 15, 16, 20, 24, 25]:
        slides = paginate_day(date(2026, 7, 16), _events(count))
        for slide in slides:
            if slide.has_featured:
                assert len(slide.events) <= 7, f"Featured slide with {len(slide.events)} exceeds 7"
            else:
                assert len(slide.events) <= 8, f"Regular slide with {len(slide.events)} exceeds 8"


def test_paginate_day_page_numbering() -> None:
    """Page numbers and counts are correct."""
    slides = paginate_day(date(2026, 7, 16), _events(20))
    page_numbers = [s.page_number for s in slides]
    page_counts = [s.page_count for s in slides]
    assert page_numbers == [1, 2, 3]
    assert all(count == 3 for count in page_counts)


def test_build_day_slides_across_multiple_days() -> None:
    grouped: OrderedDict = OrderedDict()
    grouped[date(2026, 7, 16)] = _events(2, "2026-07-16")
    grouped[date(2026, 7, 17)] = _events(9, "2026-07-17")

    slides = build_day_slides(grouped)

    # Day 1: 2 events → 1 slide
    # Day 2: 9 events → 2 slides (8 + 1)
    assert len(slides) == 3
    assert slides[0].day == date(2026, 7, 16)
    assert len(slides[0].events) == 2
    assert slides[1].day == date(2026, 7, 17)
    assert len(slides[1].events) == 8
    assert slides[2].day == date(2026, 7, 17)
    assert len(slides[2].events) == 1
