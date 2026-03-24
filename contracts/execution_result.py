from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel


class ExecutionTelemetry(BaseModel):
    capture_confidence: Optional[float] = None
    semantic_confidence: Optional[float] = None
    resolution_confidence: Optional[float] = None


class ExecutionResult(BaseModel):
    execution_id: str
    intent_id: str
    resolution_id: str
    status: Literal["success", "failed", "partial", "aborted"]
    effect_verified: bool = False
    verification_type: Optional[
        Literal["screen_diff", "dom_change", "toast", "grid_change", "manual"]
    ] = None
    observed_outcome: Optional[str] = None
    duration_ms: int = 0
    telemetry: ExecutionTelemetry = ExecutionTelemetry()
    error_code: Optional[str] = None
    error_message: Optional[str] = None