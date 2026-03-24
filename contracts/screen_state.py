from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class VisibleElementHint(BaseModel):
    kind: str
    label: Optional[str] = None
    role: Optional[str] = None


class ScreenState(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    fingerprint: Optional[str] = None
    frame_count: int = 0
    active_element_label: Optional[str] = None
    modal_open: bool = False
    visible_text_excerpt: Optional[str] = None
    primary_area: Optional[str] = None
    visible_hints: list[VisibleElementHint] = Field(default_factory=list)