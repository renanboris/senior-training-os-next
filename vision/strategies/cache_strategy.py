from __future__ import annotations

from typing import Optional
from uuid import uuid4

from contracts.resolved_target import (
    ResolutionEvidence,
    ResolvedNode,
    ResolvedTarget,
)
from vision.strategies.base import ResolutionContext, Strategy


class CacheStrategy(Strategy):
    name = "cache"

    def __init__(self, cache_lookup):
        self.cache_lookup = cache_lookup

    async def try_resolve(self, page, ctx: ResolutionContext) -> Optional[ResolvedTarget]:
        cache_hit = self.cache_lookup(ctx.intent.semantic_target)
        if not cache_hit:
            return None

        selector = cache_hit.get("selector")
        iframe = cache_hit.get("iframe")
        coords_rel = cache_hit.get("coords_rel")

        if not any([selector, iframe, coords_rel]):
            return None

        return ResolvedTarget(
            resolution_id=f"res_{uuid4().hex[:12]}",
            intent_id=ctx.intent.intent_id,
            strategy_used="cache",
            resolved_target=ResolvedNode(
                selector=selector,
                iframe=iframe,
                coords_rel=coords_rel,
            ),
            resolution_confidence=float(cache_hit.get("confidence", 0.85)),
            evidence=ResolutionEvidence(
                matched_label=ctx.intent.semantic_target,
                screen_fingerprint=ctx.screen_state.fingerprint,
            ),
            fallback_chain=["cache_hit"],
            needs_extra_validation=ctx.intent.goal_type in {"save", "delete", "confirm"},
        )