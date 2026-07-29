"""Pure text and placeholder helpers used only for rendering.

Nothing here ever mutates the source event data — these produce
*_display values for the templates while the original fields stay
untouched, so re-rendering or exporting raw data later is always safe.
"""

from __future__ import annotations

import base64
import hashlib

_PALETTE = ["#2C2A4A", "#4B3F72", "#6B5B95", "#B98EAD", "#8C7AA9"]


def truncate_text(text: str, max_length: int, *, ellipsis: str = "…") -> str:
    """Shorten text for display only, never used to alter stored data."""
    stripped = text.strip()
    if len(stripped) <= max_length:
        return stripped
    cut = stripped[: max_length - len(ellipsis)].rstrip()
    return f"{cut}{ellipsis}"


def placeholder_color(seed: str) -> str:
    """Deterministic color from the design palette, derived from a seed string."""
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(_PALETTE)
    return _PALETTE[index]


def placeholder_poster_data_uri(category: str) -> str:
    """Inline SVG placeholder poster, used when no real affiche is provided.

    Returned as a base64 data: URI so Playwright renders it with zero
    network calls and zero extra files.
    """
    color = placeholder_color(category)
    initial = (category.strip()[:1] or "?").upper()
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">'
        f'<rect width="100%" height="100%" fill="{color}"/>'
        '<text x="50%" y="50%" font-size="160" font-family="Georgia, serif" '
        f'fill="#F4E9DA" text-anchor="middle" dominant-baseline="central">{initial}</text>'
        "</svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
