from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field
from contracts.observed_action import RelativeBox


class ResolutionEvidence(BaseModel):
    matched_label: Optional[str] = None
    matched_role: Optional[str] = None
    matched_text: Optional[str] = None
    screen_fingerprint: Optional[str] = None
    frame_path: Optional[str] = None


class ResolvedNode(BaseModel):
    selector: Optional[str] = None
    iframe: Optional[str] = None
    coords_rel: Optional[RelativeBox] = None
    active_element: bool = False


class ResolvedTarget(BaseModel):
    resolution_id: str
    intent_id: str
    strategy_used: Literal[
        "cache",
        "active_element",
        "seniorx_heuristic",
        "dom",
        "frame",
        "vision",
        "coordinates",
    ]
    resolved_target: ResolvedNode
    resolution_confidence: float = Field(default=0.5, ge=0, le=1)
    evidence: ResolutionEvidence = ResolutionEvidence()
    fallback_chain: list[str] = []
    needs_extra_validation: bool = False