"""Apps Script payload adaptation into the internal generation request."""

from __future__ import annotations

from app.core.config import Settings
from app.schemas.events import WeekRequest
from app.services.payload_adapter import to_generation_request


def _payload() -> WeekRequest:
    return WeekRequest.model_validate(
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
            "events": [
                {
                    "id": "EVT-0001",
                    "date": "2026-07-16",
                    "dateLabel": "Jeudi 16 juillet",
                    "venue": "3 Brasseurs",
                    "venueId": "3BR",
                    "type": "Concert",
                    "eventName": "Concert variétés",
                    "artists": "Artiste invité",
                    "startTime": "20:00",
                    "endTime": "22:00",
                    "price": "",
                    "visualUrl": "",
                    "featured": False,
                    "status": "Validé",
                    "sourceUrl": "",
                }
            ],
        }
    )


def test_payload_adapter_uses_default_city() -> None:
    request = to_generation_request(_payload(), Settings(api_key="test-key"))
    assert request.city == "Le Havre"


def test_payload_adapter_uses_environment_city_override() -> None:
    request = to_generation_request(_payload(), Settings(api_key="test-key", city="Rouen"))
    assert request.city == "Rouen"


def test_payload_adapter_uses_iso_week_number() -> None:
    payload = WeekRequest.model_validate(
        {
            "project": "nuit-blanche",
            "template": "nuit-blanche",
            "week": {
                "label": "Semaine 1 – du 29/12/2025 au 04/01/2026",
                "startDate": "2025-12-29",
                "endDate": "2026-01-04",
            },
            "events": [
                {
                    "id": "EVT-0001",
                    "date": "2025-12-29",
                    "dateLabel": "Lundi 29 décembre",
                    "venue": "3 Brasseurs",
                    "type": "Concert",
                    "eventName": "Concert variétés",
                }
            ],
        }
    )
    request = to_generation_request(payload, Settings(api_key="test-key"))
    assert request.week_number == 1
