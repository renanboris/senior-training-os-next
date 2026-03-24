from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class KnownSkill(BaseModel):
    skill_id: str
    semantic_target: str
    goal_type: str
    screen_fingerprint: Optional[str] = None
    preferred_selector: Optional[str] = None
    preferred_iframe: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    source: str = 'legacy_json'