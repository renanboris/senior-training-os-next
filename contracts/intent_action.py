from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ExpectedEffect(BaseModel):
    effect_type: Literal[
        "screen_change",
        "grid_refresh",
        "modal_open",
        "modal_close",
        "field_filled",
        "filter_applied",
        "toast_visible",
        "download_started",
        "upload_completed",
        "record_saved",
    ]
    description: str
    verification_hint: Optional[str] = None


class IntentAction(BaseModel):
    intent_id: str
    source_event_id: Optional[str] = None
    goal_type: Literal[
        "navigate",
        "open",
        "search",
        "filter",
        "fill",
        "select",
        "confirm",
        "save",
        "delete",
        "upload",
        "download",
        "expand",
        "close",
    ]
    business_entity: Optional[str] = None
    semantic_target: str
    ui_context: Optional[str] = None
    expected_effect: ExpectedEffect
    pedagogical_value: Optional[str] = None
    semantic_confidence: float = Field(default=0.5, ge=0, le=1)
    reasoning_trace: list[str] = []