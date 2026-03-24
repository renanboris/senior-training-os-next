from __future__ import annotations

import time
from uuid import uuid4

from contracts.execution_result import ExecutionResult, ExecutionTelemetry
from contracts.intent_action import IntentAction
from contracts.resolved_target import ResolvedTarget
from contracts.observed_action import ScreenSnapshot
from runtime.effect_verifier import EffectVerifier
from runtime.ui_overlays import remove_subtitle, show_subtitle, update_progress_pill


class ActionExecutor:
    def __init__(self, click_adapter, type_adapter):
        self.click_adapter = click_adapter
        self.type_adapter = type_adapter
        self.verifier = EffectVerifier()

    async def execute(
        self,
        page,
        intent: IntentAction,
        target: ResolvedTarget,
        before_snapshot: ScreenSnapshot,
        step_index: int,
        total_steps: int,
        lesson_name: str,
        subtitle_text: str | None = None,
    ) -> ExecutionResult:
        started = time.perf_counter()

        await update_progress_pill(page, step_index, total_steps, lesson_name)
        if subtitle_text:
            await show_subtitle(page, subtitle_text)

        if target.resolved_target.active_element:
            if intent.goal_type in {"fill", "search"} and subtitle_text:
                await self.type_adapter(page, subtitle_text)
        elif target.resolved_target.selector:
            await self.click_adapter(page, target.resolved_target.selector)
        elif target.resolved_target.coords_rel:
            await self.click_adapter(page, target.resolved_target.coords_rel)
        else:
            raise RuntimeError("ResolvedTarget sem alvo executável.")

        after_snapshot = ScreenSnapshot(
            url=page.url,
            title=await page.title(),
            frame_count=len(page.frames),
            modal_open=await page.evaluate(
                """
                () => !!document.querySelector('.p-dialog-mask, .cdk-overlay-pane, [role="dialog"], .modal, .mat-dialog-container')
                """
            ),
        )

        verified, outcome = self.verifier.verify(intent, before_snapshot, after_snapshot)
        await remove_subtitle(page)

        return ExecutionResult(
            execution_id=f"exe_{uuid4().hex[:12]}",
            intent_id=intent.intent_id,
            resolution_id=target.resolution_id,
            status="success" if verified else "partial",
            effect_verified=verified,
            verification_type="dom_change" if verified else None,
            observed_outcome=outcome,
            duration_ms=int((time.perf_counter() - started) * 1000),
            telemetry=ExecutionTelemetry(
                semantic_confidence=intent.semantic_confidence,
                resolution_confidence=target.resolution_confidence,
            ),
        )