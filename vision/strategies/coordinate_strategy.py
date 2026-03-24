from __future__ import annotations

from typing import Optional
from uuid import uuid4

from contracts.observed_action import RelativeBox
from contracts.resolved_target import ResolutionEvidence, ResolvedNode, ResolvedTarget
from vision.strategies.base import ResolutionContext, Strategy


class CoordinateStrategy(Strategy):
    name = "coordinates"

    def __init__(self, coordinate_lookup):
        self.coordinate_lookup = coordinate_lookup

    async def try_resolve(self, page, ctx: ResolutionContext) -> Optional[ResolvedTarget]:
        coords = self.coordinate_lookup(ctx.intent.semantic_target)
        if not coords:
            return None

        return ResolvedTarget(
            resolution_id=f"res_{uuid4().hex[:12]}",
            intent_id=ctx.intent.intent_id,
            strategy_used="coordinates",
            resolved_target=ResolvedNode(
                coords_rel=RelativeBox(**coords),
            ),
            resolution_confidence=0.58,
            evidence=ResolutionEvidence(
                matched_label=ctx.intent.semantic_target,
                screen_fingerprint=ctx.screen_state.fingerprint,
            ),
            fallback_chain=["cache_miss", "dom_miss", "frame_miss", "vision_miss", "coordinate_success"],
            needs_extra_validation=True,
        )