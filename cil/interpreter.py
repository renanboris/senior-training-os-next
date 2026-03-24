from __future__ import annotations

from uuid import uuid4

from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.observed_action import ObservedAction
from contracts.screen_state import ScreenState


class IntentInterpreter:
    def interpret(self, observed: ObservedAction, state: ScreenState) -> IntentAction:
        goal_type = self._infer_goal_type(observed)
        semantic_target = self._infer_semantic_target(observed)
        entity = self._infer_business_entity(observed, state)
        expected_effect = self._infer_expected_effect(observed)
        reasoning = self._build_reasoning_trace(observed, state, goal_type, semantic_target)

        return IntentAction(
            intent_id=f"int_{uuid4().hex[:12]}",
            source_event_id=observed.event_id,
            goal_type=goal_type,
            business_entity=entity,
            semantic_target=semantic_target,
            ui_context=state.primary_area,
            expected_effect=expected_effect,
            pedagogical_value=self._infer_pedagogical_value(goal_type, entity, semantic_target),
            semantic_confidence=self._score_semantic_confidence(observed, state, semantic_target),
            reasoning_trace=reasoning,
        )

    def _infer_goal_type(self, observed: ObservedAction) -> str:
        if observed.action_type == 'type_and_enter':
            return 'search'
        if observed.action_type == 'type':
            return 'fill'

        label = (observed.raw_target.text or observed.raw_target.aria_label or '').lower()
        if any(k in label for k in ['pesquisar', 'buscar', 'procurar', 'filtrar']):
            return 'search'
        if any(k in label for k in ['salvar', 'gravar']):
            return 'save'
        if 'confirmar' in label:
            return 'confirm'
        if any(k in label for k in ['excluir', 'remover', 'apagar']):
            return 'delete'
        if any(k in label for k in ['abrir', 'detalhar', 'visualizar']):
            return 'open'
        return 'navigate'

    def _infer_semantic_target(self, observed: ObservedAction) -> str:
        for candidate in [
            observed.raw_target.text,
            observed.raw_target.aria_label,
            observed.raw_target.name,
            observed.raw_target.role,
            observed.raw_target.tag,
        ]:
            if candidate and str(candidate).strip():
                return str(candidate).strip()
        return 'alvo não identificado'

    def _infer_business_entity(self, observed: ObservedAction, state: ScreenState) -> str | None:
        blob = ' '.join(
            filter(
                None,
                [
                    observed.raw_target.text,
                    observed.raw_target.aria_label,
                    observed.typed_value,
                    state.visible_text_excerpt,
                    state.title,
                    state.url,
                ],
            )
        ).lower()

        if 'cliente' in blob:
            return 'cliente'
        if 'fornecedor' in blob:
            return 'fornecedor'
        if 'pedido' in blob:
            return 'pedido'
        if 'documento' in blob or 'ged' in blob:
            return 'documento'
        if 'filial' in blob:
            return 'filial'
        return None

    def _infer_expected_effect(self, observed: ObservedAction) -> ExpectedEffect:
        sc = observed.state_change
        if sc and sc.change_type == 'modal_open':
            return ExpectedEffect(effect_type='modal_open', description='Abertura de modal após a ação.')
        if sc and sc.change_type == 'modal_close':
            return ExpectedEffect(effect_type='modal_close', description='Fechamento de modal após a ação.')
        if sc and sc.change_type == 'navigation':
            return ExpectedEffect(effect_type='screen_change', description='Mudança de tela ou URL após a ação.')
        if observed.action_type == 'type_and_enter':
            return ExpectedEffect(effect_type='grid_refresh', description='Atualização de lista ou grade após pesquisa.')
        if observed.action_type == 'type':
            return ExpectedEffect(effect_type='field_filled', description='Campo preenchido corretamente.')
        return ExpectedEffect(effect_type='screen_change', description='Algum efeito visível deve ocorrer após a ação.')

    def _infer_pedagogical_value(self, goal_type: str, entity: str | None, semantic_target: str) -> str:
        entity_txt = entity or 'registro'
        return f"Ensina como {goal_type} relacionado a {entity_txt} usando o alvo '{semantic_target}'."

    def _score_semantic_confidence(self, observed: ObservedAction, state: ScreenState, semantic_target: str) -> float:
        score = 0.45
        if observed.capture_confidence >= 0.8:
            score += 0.2
        if semantic_target != 'alvo não identificado':
            score += 0.15
        if observed.state_change and observed.state_change.changed:
            score += 0.1
        if state.primary_area:
            score += 0.05
        return min(score, 0.98)

    def _build_reasoning_trace(self, observed: ObservedAction, state: ScreenState, goal_type: str, semantic_target: str) -> list[str]:
        trace = [f"action_type={observed.action_type}", f"goal_type={goal_type}"]
        if semantic_target:
            trace.append(f"semantic_target={semantic_target}")
        if observed.state_change and observed.state_change.change_type:
            trace.append(f"state_change={observed.state_change.change_type}")
        if state.primary_area:
            trace.append(f"ui_context={state.primary_area}")
        return trace