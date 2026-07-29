"""Group sorted events by calendar day, preserving day order."""

from __future__ import annotations

from collections import OrderedDict
from datetime import date as Date

from app.services.normalizer import NormalizedEvent


def group_by_day(sorted_events: list[NormalizedEvent]) -> OrderedDict[Date, list[NormalizedEvent]]:
    groups: OrderedDict[Date, list[NormalizedEvent]] = OrderedDict()
    for event in sorted_events:
        groups.setdefault(event.date, []).append(event)
    return groups
