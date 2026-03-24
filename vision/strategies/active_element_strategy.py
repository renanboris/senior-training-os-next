from __future__ import annotations

from typing import Optional
from uuid import uuid4

from contracts.resolved_target import ResolutionEvidence, ResolvedNode, ResolvedTarget
from vision.strategies.base import ResolutionContext, Strategy


class ActiveElementStrategy(Strategy):
    name = "active_element"

    async def try_resolve(self, page, ctx: ResolutionContext) -> Optional[ResolvedTarget]:
        active_info = await page.evaluate(
            """
            () => {
                const el = document.activeElement;
                if (!el) return null;
                return {
                    tag: el.tagName?.toLowerCase() || null,
                    ariaLabel: el.getAttribute('aria-label'),
                    name: el.getAttribute('name'),
                    placeholder: el.getAttribute('placeholder')
                };
            }
            """
        )

        if not active_info:
            return None

        label = active_info.get("ariaLabel") or active_info.get("name") or active_info.get("placeholder")
        if not label:
            return None

        return ResolvedTarget(
            resolution_id=f"res_{uuid4().hex[:12]}",
            intent_id=ctx.intent.intent_id,
            strategy_used="active_element",
            resolved_target=ResolvedNode(active_element=True),
            resolution_confidence=0.72,
            evidence=ResolutionEvidence(
                matched_label=label,
                matched_role=active_info.get("tag"),
                screen_fingerprint=ctx.screen_state.fingerprint,
            ),
            fallback_chain=["cache_miss", "active_element_success"],
            needs_extra_validation=ctx.intent.goal_type in {"save", "delete", "confirm"},
        )