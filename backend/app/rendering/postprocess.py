"""Pillow-based post-processing: verify exact slide dimensions and optimize PNGs."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def finalize_png(path: Path, expected_width: int, expected_height: int) -> None:
    """Verify the screenshot matches the expected canvas and re-save it optimized.

    Guards against distorted or mis-sized slides slipping through before
    they get zipped and handed to the client.
    """
    with Image.open(path) as image:
        if image.size != (expected_width, expected_height):
            raise ValueError(
                f"{path.name}: expected {expected_width}x{expected_height}, got "
                f"{image.size[0]}x{image.size[1]}"
            )
        rgb_image = image.convert("RGB")
        rgb_image.save(path, format="PNG", optimize=True)
