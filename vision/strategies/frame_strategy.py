from __future__ import annotations

from typing import Optional
from uuid import uuid4

from contracts.resolved_target import ResolutionEvidence, ResolvedNode, ResolvedTarget
from vision.strategies.base import ResolutionContext, Strategy


class FrameStrategy(Strategy):
    name = "frame"

    async def try_resolve(self, page, ctx: ResolutionContext) -> Optional[ResolvedTarget]:
        target_text = ctx.intent.semantic_target.strip()
        if not target_text:
            return None

        for idx, frame in enumerate(page.frames):
            locator = frame.get_by_text(target_text, exact=False)
            count = await locator.count()
            if count > 0:
                return ResolvedTarget(
                    resolution_id=f"res_{uuid4().hex[:12]}",
                    intent_id=ctx.intent.intent_id,
                    strategy_used="frame",
                    resolved_target=ResolvedNode(
                        selector=f"frame_text:{target_text}",
                        iframe=f"frame[{idx}]",
                    ),
                    resolution_confidence=0.8,
                    evidence=ResolutionEvidence(
                        matched_text=target_text,
                        frame_path=f"frame[{idx}]",
                        screen_fingerprint=ctx.screen_state.fingerprint,
                    ),
                    fallback_chain=["cache_miss", "dom_miss", "frame_match_success"],
                    needs_extra_validation=ctx.intent.goal_type in {"save", "delete", "confirm"},
                )

        return None 