"""Density-based template selection."""

from __future__ import annotations

import pytest

from app.services.layout import estimate_density


@pytest.mark.parametrize(
    ("count", "expected_template"),
    [
        (1, "spacious"),
        (4, "spacious"),
        (5, "standard"),
        (6, "standard"),
        (7, "compact"),
        (8, "compact"),
    ],
)
def test_estimate_density(count: int, expected_template: str) -> None:
    assert estimate_density(count) == expected_template
