"""Price flow from payload to rendered HTML."""

from __future__ import annotations

from app.rendering.renderer import render_slide
from app.schemas.events import EventIn
from app.services.generation_service import _event_to_context
from app.services.normalizer import NO_PRICE_LABEL, normalize_event


def _render_price(price: object) -> str:
    event = EventIn.model_validate(
        {
            "id": "EVT-0001",
            "date": "2026-07-16",
            "dateLabel": "Jeudi 16 juillet",
            "venue": "3 Brasseurs",
            "type": "Concert",
            "eventName": "Concert variétés",
            "price": price,
        }
    )
    normalized = normalize_event(event)
    return render_slide(
        "day.html",
        {
            "slide_type": "day",
            "topbar_variant": "section",
            "week_number": 32,
            "city": "Le Havre",
            "day_name": "jeudi",
            "day_date_label": "16 juillet 2026",
            "template": "compact",
            "events": [_event_to_context(normalized)],
            "page_label": "Jeudi",
        },
    )


def test_price_present_in_payload_is_rendered() -> None:
    html = _render_price("12 €")
    assert "12 €" in html


def test_empty_price_uses_fallback() -> None:
    html = _render_price("")
    assert NO_PRICE_LABEL in html


def test_gratuit_price_is_rendered() -> None:
    html = _render_price("Gratuit")
    assert "Gratuit" in html


def test_complex_price_text_is_rendered() -> None:
    html = _render_price("10 € + 1 consommation")
    assert "10 € + 1 consommation" in html


def test_long_free_text_price_is_rendered() -> None:
    html = _render_price("Prévente 12 €, sur place 15 €, adhérents 8 €")
    assert "Prévente 12 €, sur place 15 €, adhérents 8 €" in html
