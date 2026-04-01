from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class RelativeBox(BaseModel):
    x_pct: float = Field(ge=0, le=1)
    y_pct: float = Field(ge=0, le=1)
    w_pct: float = Field(ge=0, le=1)
    h_pct: float = Field(ge=0, le=1)


class RawTarget(BaseModel):
    selector: Optional[str] = None
    tag: Optional[str] = None
    text: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None
    aria_label: Optional[str] = None
    iframe_hint: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    coords_rel: Optional[RelativeBox] = None


class Artifacts(BaseModel):
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    html_snapshot: Optional[str] = None


class StateChange(BaseModel):
    changed: bool = False
    change_type: Literal[
        "none",
        "navigation",
        "modal_open",
        "modal_close",
        "grid_refresh",
        "field_update",
        "toast",
        "accordion_expand",
        "accordion_collapse",
    ] = "none"
    change_summary: Optional[str] = None


class ScreenSnapshot(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    fingerprint: Optional[str] = None
    sidebar_active: Optional[str] = None
    modal_open: bool = False
    frame_count: int = 0
    grid_row_count: int = 0
    toast_present: bool = False


class ObservedAction(BaseModel):
    event_id: str
    timestamp: datetime
    action_type: Literal[
        "click",
        "double_click",
        "hover",
        "type",
        "type_and_enter",
        "select_option",
        "checkbox_toggle",
        "keypress",
        "upload",
    ]
    raw_target: RawTarget
    typed_value: Optional[str] = None
    screen_before: ScreenSnapshot
    screen_after: Optional[ScreenSnapshot] = None
    state_change: Optional[StateChange] = None
    artifacts: Artifacts = Artifacts()
    capture_confidence: float = Field(default=0.5, ge=0, le=1)
    risk_class: Literal["low", "medium", "high"] = "low"