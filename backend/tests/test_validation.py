"""Validation of incoming events and week requests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.events import EventIn, WeekRequest


def _base_event(**overrides: object) -> dict[str, object]:
    event = {
        "external_id": "event-001",
        "date": "2026-07-16",
        "start_time": "20:00",
        "venue": "3 Brasseurs",
        "category": "Concert",
        "title": "Concert variétés",
    }
    event.update(overrides)
    return event


def test_event_requires_core_fields() -> None:
    with pytest.raises(ValidationError):
        EventIn.model_validate({"external_id": "x", "date": "2026-07-16"})


def test_event_optional_fields_default_to_none() -> None:
    event = EventIn.model_validate(_base_event())
    assert event.artist is None
    assert event.description is None
    assert event.price is None
    assert event.poster_url is None
    assert event.featured is False


def test_event_blank_optional_strings_become_none() -> None:
    event = EventIn.model_validate(_base_event(artist="   ", price=""))
    assert event.artist is None
    assert event.price is None


def test_event_required_strings_are_stripped() -> None:
    event = EventIn.model_validate(_base_event(title="  Concert variétés  "))
    assert event.title == "Concert variétés"


def test_week_request_valid() -> None:
    request = WeekRequest.model_validate(
        {
            "city": "Le Havre",
            "week_number": 29,
            "start_date": "2026-07-16",
            "end_date": "2026-07-22",
            "events": [_base_event()],
        }
    )
    assert request.week_number == 29
    assert len(request.events) == 1


def test_week_request_rejects_end_before_start() -> None:
    with pytest.raises(ValidationError):
        WeekRequest.model_validate(
            {
                "city": "Le Havre",
                "week_number": 29,
                "start_date": "2026-07-22",
                "end_date": "2026-07-16",
                "events": [_base_event()],
            }
        )


def test_week_request_rejects_out_of_range_week_number() -> None:
    with pytest.raises(ValidationError):
        WeekRequest.model_validate(
            {
                "city": "Le Havre",
                "week_number": 54,
                "start_date": "2026-07-16",
                "end_date": "2026-07-22",
                "events": [_base_event()],
            }
        )
