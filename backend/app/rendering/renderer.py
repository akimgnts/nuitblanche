"""Jinja2 rendering: turns a slide context dict into an HTML string."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
STATIC_CSS_PATH = Path(__file__).resolve().parent.parent / "static" / "css" / "styles.css"


@lru_cache(maxsize=1)
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


@lru_cache(maxsize=1)
def _inline_css() -> str:
    return STATIC_CSS_PATH.read_text(encoding="utf-8")


def render_slide(template_name: str, context: dict[str, object]) -> str:
    """Render one slide template to a full HTML document string."""
    template = _environment().get_template(template_name)
    return template.render(inline_css=_inline_css(), **context)
