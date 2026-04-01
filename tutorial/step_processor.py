from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from capture.shadow_ingestion import normalize_goal_type
from cil.interpreter import IntentInterpreter
from cil.observer import ScreenObserver
from cil.skill_memory import SkillMemory
from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.observed_action import (
    ObservedAction,
    RawTarget,
    RelativeBox,
    ScreenSnapshot,
)
from contracts.screen_state import ScreenState
from runtime.ui_overlays import remove_subtitle, safe_evaluate, show_subtitle, update_progress_pill
from tutorial.highlight import ElementHighlight
from tutorial.humanizer import HumanizedDelay
from vision.resolver import TargetResolver
from vision.strategies.base import ResolutionContext


@dataclass
class StepResult:
    step_index: int
    event_id: str
    status: Literal["success", "resolution_failed", "execution_partial", "skipped"]
    audio_file: Optional[str] = None
    audio_duration: float = 0.0
    strategy_used: Optional[str] = None
    error: Optional[str] = None


class StepProcessor:
    """Processa um único shadow_event: navega, resolve, destaca, narra e executa."""

    def __init__(
        self,
        mode: Literal["replay", "guide", "record-only"],
        resolver: TargetResolver,
        executor,
        highlight: ElementHighlight,
        observer: ScreenObserver,
        interpreter: IntentInterpreter,
        skill_memory: SkillMemory,
        humanizer: HumanizedDelay,
    ) -> None:
        self.mode = mode
        self.resolver = resolver
        self.executor = executor
        self.highlight = highlight
        self.observer = observer
        self.interpreter = interpreter
        self.skill_memory = skill_memory
        self.humanizer = humanizer

    async def process(
        self,
        page,
        event: dict,
        step_index: int,
        total_steps: int,
        lesson_name: str,
        audio_file: Optional[str] = None,
        audio_duration: float = 0.0,
    ) -> StepResult:
        event_id = f"shadow_{event.get('id_acao', uuid4().hex[:8])}"

        # 1. Navega para a URL do evento se necessário
        await self._navigate_if_needed(page, event)

        # 2. Observa o estado atual da tela
        try:
            state = await self.observer.observe(page)
        except Exception:
            state = ScreenState(url=page.url if hasattr(page, "url") else None)

        # 3. Constrói IntentAction e ObservedAction
        intent = self._build_intent(event, state)
        observed = self._build_observed(event)

        # 4. Recupera skills relevantes
        known_skills = self.skill_memory.retrieve(state, intent)

        # 5. Resolve o alvo semântico
        iframe_hint = (event.get("elemento_alvo") or {}).get("iframe_hint")
        ctx = ResolutionContext(
            intent=intent,
            screen_state=state,
            known_skills=[s.model_dump() for s in known_skills],
        )
        # Propaga iframe_hint via campo extra no contexto
        if iframe_hint:
            ctx.known_skills.append({"_iframe_hint": iframe_hint})

        try:
            resolved, trace = await self.resolver.resolve(page, ctx)
        except RuntimeError as exc:
            return StepResult(
                step_index=step_index,
                event_id=event_id,
                status="resolution_failed",
                audio_file=audio_file,
                audio_duration=audio_duration,
                error=str(exc),
            )

        strategy_used = resolved.strategy_used

        # 6. Overlays visuais (replay e guide)
        if self.mode != "record-only":
            coords_rel = resolved.resolved_target.coords_rel
            selector = resolved.resolved_target.selector
            await self.highlight.inject(page, coords_rel=coords_rel, selector=selector)
            await show_subtitle(page, intent.pedagogical_value or "")
            await update_progress_pill(page, step_index, total_steps, lesson_name)

        # 7. Executa a ação (apenas replay)
        status: Literal["success", "resolution_failed", "execution_partial", "skipped"] = "success"
        if self.mode == "replay" and self.executor is not None:
            try:
                before_snapshot = ScreenSnapshot(
                    url=page.url if hasattr(page, "url") else None,
                    title=await page.title() if hasattr(page, "title") else None,
                )
                result = await self.executor.execute(
                    page=page,
                    intent=intent,
                    target=resolved,
                    before_snapshot=before_snapshot,
                    step_index=step_index,
                    total_steps=total_steps,
                    lesson_name=lesson_name,
                    subtitle_text=intent.pedagogical_value,
                )
                if result.status in {"partial", "failed"}:
                    status = "execution_partial"
            except Exception as exc:
                status = "execution_partial"

        # 8. Remove overlays
        if self.mode != "record-only":
            await self.highlight.remove(page)
            await remove_subtitle(page)

        # 9. Delay humanizado
        if self.mode == "record-only":
            await asyncio.sleep(2.0)
        else:
            await self.humanizer.wait(audio_duration)

        return StepResult(
            step_index=step_index,
            event_id=event_id,
            status=status,
            audio_file=audio_file,
            audio_duration=audio_duration,
            strategy_used=strategy_used,
        )

    async def _navigate_if_needed(self, page, event: dict) -> None:
        """Navega para a URL do evento se diferente da URL atual."""
        ctx = event.get("contexto_semantico") or {}
        tela = ctx.get("tela_atual") or {}
        event_url = tela.get("url")

        if not event_url:
            return

        current_url = page.url if hasattr(page, "url") else ""
        if event_url == current_url:
            return

        try:
            await page.goto(event_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(0.8)
        except Exception as exc:
            print(f"  [aviso] Nao navegou para {event_url[:60]}: {exc}")

    def _build_intent(self, event: dict, state: ScreenState) -> IntentAction:
        """Constrói IntentAction a partir de um shadow_event."""
        goal_type = normalize_goal_type(event)
        target = (
            (event.get("business_target") or "").strip()
            or (event.get("elemento_alvo") or {}).get("label_curto", "")
            or "alvo nao identificado"
        )
        narration = event.get("micro_narracao") or event.get("intencao_semantica") or ""
        url = (event.get("contexto_semantico") or {}).get("tela_atual", {}).get("url")

        return IntentAction(
            intent_id=f"int_{uuid4().hex[:12]}",
            goal_type=goal_type,
            semantic_target=target,
            ui_context=url or state.primary_area,
            expected_effect=ExpectedEffect(
                effect_type="screen_change",
                description="Efeito esperado apos a acao.",
            ),
            pedagogical_value=narration,
            semantic_confidence=0.8,
        )

    def _build_observed(self, event: dict) -> ObservedAction:
        """Constrói ObservedAction a partir de um shadow_event."""
        el = event.get("elemento_alvo") or {}
        ctx = (event.get("contexto_semantico") or {}).get("tela_atual") or {}

        acao = (event.get("acao") or "clique").lower()
        action_map = {
            "clique": "click",
            "duplo_clique": "double_click",
            "digitar": "type",
            "digitar_e_enter": "type_and_enter",
            "selecionar": "select_option",
            "hover": "hover",
            "upload": "upload",
        }
        action_type = action_map.get(acao, "click")

        cr = el.get("coordenadas_relativas") or {}
        coords_rel = None
        if cr:
            try:
                coords_rel = RelativeBox(
                    x_pct=float(cr.get("x_pct", 0.5)),
                    y_pct=float(cr.get("y_pct", 0.5)),
                    w_pct=float(cr.get("w_pct", 0.05)),
                    h_pct=float(cr.get("h_pct", 0.05)),
                )
            except Exception:
                pass

        raw_target = RawTarget(
            selector=el.get("seletor_hint"),
            tag=el.get("tipo_elemento"),
            text=event.get("business_target") or el.get("label_curto"),
            aria_label=el.get("label_curto"),
            iframe_hint=el.get("iframe_hint"),
            coords_rel=coords_rel,
        )

        cmap = {"alta": 0.9, "media": 0.7, "baixa": 0.45}
        conf = cmap.get((el.get("confianca_captura") or "media").lower(), 0.7)

        return ObservedAction(
            event_id=f"shadow_{event.get('id_acao', uuid4().hex[:8])}",
            timestamp=datetime.now(timezone.utc),
            action_type=action_type,
            raw_target=raw_target,
            typed_value=event.get("valor_input") or None,
            screen_before=ScreenSnapshot(
                url=ctx.get("url"),
                title=ctx.get("tela_id"),
                fingerprint=ctx.get("tela_id"),
            ),
            capture_confidence=conf,
            risk_class="low",
        )
