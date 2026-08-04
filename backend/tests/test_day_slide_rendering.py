"""Rendered day slide should keep the uniform 8-card system."""

from __future__ import annotations

from app.rendering.renderer import render_slide


def test_day_slide_css_uses_uniform_grid_and_a4_posters() -> None:
    html = render_slide(
        "day.html",
        {
            "slide_type": "day",
            "topbar_variant": "section",
            "week_number": 32,
            "city": "Le Havre",
            "day_name": "samedi",
            "day_date_label": "25 juillet 2026",
            "template": "compact",
            "events": [
                {
                    "title_display": "Concert variétés",
                    "artist_display": "Artiste invité",
                    "description_display": None,
                    "venue": "3 Brasseurs",
                    "category": "Concert",
                    "price_display": "12€",
                    "poster_url": None,
                    "placeholder_color": "#123456",
                    "poster_label": "Concert variétés",
                    "featured": True,
                    "start_time_label": "20h",
                }
            ],
            "page_label": "Samedi 1/2",
        },
    )

    assert "grid-template-rows: repeat(4, minmax(0, 1fr));" in html
    assert "aspect-ratio: 1 / 1.4142;" in html
    assert "grid-column: 1 / -1;" not in html
    assert ".event.featured .poster {" not in html
