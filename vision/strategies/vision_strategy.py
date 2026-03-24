from __future__ import annotations

from typing import Optional
from uuid import uuid4

from contracts.observed_action import RelativeBox
from contracts.resolved_target import ResolutionEvidence, ResolvedNode, ResolvedTarget
from vision.strategies.base import ResolutionContext, Strategy


class VisionStrategy(Strategy):
    name = "vision"

    def __init__(self, infer_with_llm):
        self.infer_with_llm = infer_with_llm

    async def try_resolve(self, page, ctx: ResolutionContext) -> Optional[ResolvedTarget]:
        result = await self.infer_with_llm(page=page, intent=ctx.intent, state=ctx.screen_state)
        if not result:
            return None

        coords = result.get("coords_rel")
        if not coords:
            return None

        return ResolvedTarget(
            resolution_id=f"res_{uuid4().hex[:12]}",
            intent_id=ctx.intent.intent_id,
            strategy_used="vision",
            resolved_target=ResolvedNode(
                coords_rel=RelativeBox(**coords),
            ),
            resolution_confidence=float(result.get("confidence", 0.7)),
            evidence=ResolutionEvidence(
                matched_label=ctx.intent.semantic_target,
                screen_fingerprint=ctx.screen_state.fingerprint,
            ),
            fallback_chain=["cache_miss", "dom_miss", "frame_miss", "vision_success"],
            needs_extra_validation=True,
        )