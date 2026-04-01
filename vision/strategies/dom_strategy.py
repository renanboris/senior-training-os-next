from __future__ import annotations

from typing import Optional
from uuid import uuid4

from contracts.resolved_target import ResolutionEvidence, ResolvedNode, ResolvedTarget
from vision.strategies.base import ResolutionContext, Strategy


class DomStrategy(Strategy):
    name = "dom"

    async def try_resolve(self, page, ctx: ResolutionContext) -> Optional[ResolvedTarget]:
        target_text = ctx.intent.semantic_target.strip()
        if not target_text:
            return None

        # Tenta por role=button
        locator = page.get_by_role("button", name=target_text)
        count = await locator.count()
        if count > 0:
            selector = f'role=button[name="{target_text}"]'
            return self._build_result(ctx, selector)

        # Tenta por label
        locator = page.get_by_label(target_text)
        count = await locator.count()
        if count > 0:
            selector = f"label={target_text}"
            return self._build_result(ctx, selector)

        # Tenta por placeholder
        locator = page.get_by_placeholder(target_text)
        count = await locator.count()
        if count > 0:
            selector = f"placeholder={target_text}"
            return self._build_result(ctx, selector)

        return None

    def _build_result(self, ctx: ResolutionContext, selector: str) -> ResolvedTarget:
        return ResolvedTarget(
            resolution_id=f"res_{uuid4().hex[:12]}",
            intent_id=ctx.intent.intent_id,
            strategy_used="dom",
            resolved_target=ResolvedNode(selector=selector),
            resolution_confidence=0.88,
            evidence=ResolutionEvidence(
                matched_label=ctx.intent.semantic_target,
                screen_fingerprint=ctx.screen_state.fingerprint,
            ),
            fallback_chain=["cache_miss", "dom_match_success"],
            needs_extra_validation=ctx.intent.goal_type in {"save", "delete", "confirm"},
        )
