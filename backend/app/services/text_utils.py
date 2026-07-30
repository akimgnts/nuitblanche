"""Pure text and placeholder helpers used only for rendering.

Nothing here ever mutates the source event data — these produce
*_display values for the templates while the original fields stay
untouched, so re-rendering or exporting raw data later is always safe.
"""

from __future__ import annotations

import hashlib

# Muted jewel tones matching the reference design's poster placeholders.
_PALETTE = [
    "#4d375f",
    "#2f6271",
    "#81506f",
    "#543d67",
    "#8e5337",
    "#a86c37",
    "#433e46",
    "#3a5565",
    "#725f56",
    "#9a4160",
]


def truncate_text(text: str, max_length: int, *, ellipsis: str = "…") -> str:
    """Shorten text for display only, never used to alter stored data."""
    stripped = text.strip()
    if len(stripped) <= max_length:
        return stripped
    cut = stripped[: max_length - len(ellipsis)].rstrip()
    return f"{cut}{ellipsis}"


def placeholder_color(seed: str) -> str:
    """Deterministic color from the design palette, derived from a seed string.

    Used as the poster background when no real affiche is available yet.
    """
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(_PALETTE)
    return _PALETTE[index]
