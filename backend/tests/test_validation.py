"""Validation of incoming events and week requests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.events import EventIn, WeekRequest


def _base_event(**overrides: object) -> dict[str, object]:
    event = {
        "id": "EVT-0001",
        "date": "2026-07-16",
        "dateLabel": "Jeudi 16 juillet",
        "startTime": "20:00",
        "venue": "3 Brasseurs",
        "type": "Concert",
        "eventName": "Concert variétés",
    }
    event.update(overrides)
    return event


def test_event_requires_core_fields() -> None:
    with pytest.raises(ValidationError):
        EventIn.model_validate({"id": "x", "date": "2026-07-16"})


def test_event_optional_fields_default_to_none() -> None:
    event = EventIn.model_validate(_base_event())
    assert event.artists is None
    assert event.price is None
    assert event.media_id is None
    assert event.visual_url is None
    assert event.featured is False


def test_event_blank_optional_strings_become_none() -> None:
    event = EventIn.model_validate(_base_event(artists="   ", price=""))
    assert event.artists is None
    assert event.price is None


def test_event_required_strings_are_stripped() -> None:
    event = EventIn.model_validate(_base_event(eventName="  Concert variétés  "))
    assert event.event_name == "Concert variétés"


def test_apps_script_week_request_valid() -> None:
    request = WeekRequest.model_validate(
        {
            "project": "nuit-blanche",
            "template": "nuit-blanche",
            "week": {
                "label": "Semaine 29 – du 16/07/2026 au 22/07/2026",
                "startDate": "2026-07-16",
                "endDate": "2026-07-22",
            },
            "options": {
                "statuses": ["Validé"],
                "sort": ["date", "startTime", "venue"],
            },
            "events": [_base_event()],
        }
    )
    assert request.project == "nuit-blanche"
    assert request.options.sort == ["date", "startTime", "venue"]
    assert len(request.events) == 1


def test_week_request_rejects_end_before_start() -> None:
    with pytest.raises(ValidationError):
        WeekRequest.model_validate(
            {
                "project": "nuit-blanche",
                "template": "nuit-blanche",
                "week": {
                    "label": "Invalid week",
                    "startDate": "2026-07-22",
                    "endDate": "2026-07-16",
                },
                "events": [_base_event()],
            }
        )


def test_event_blank_optional_strings_become_none_for_apps_script_fields() -> None:
    event = EventIn.model_validate(
        _base_event(
            artists="   ",
            price="",
            mediaId="  ",
            visualUrl="  ",
            sourceUrl=" ",
            venueId="",
        )
    )
    assert event.artists is None
    assert event.price is None
    assert event.media_id is None
    assert event.visual_url is None
    assert event.source_url is None
    assert event.venue_id is None
