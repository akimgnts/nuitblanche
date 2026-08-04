"""Single adaptation layer from Apps Script payload to the internal request."""

from __future__ import annotations

from app.core.config import Settings
from app.schemas.events import GenerationRequest, WeekRequest


def to_generation_request(payload: WeekRequest, settings: Settings) -> GenerationRequest:
    return GenerationRequest(
        project=payload.project,
        template=payload.template,
        city=settings.city,
        week_number=payload.week.start_date.isocalendar().week,
        week=payload.week,
        options=payload.options,
        events=payload.events,
        instagram_handle=None,
    )
