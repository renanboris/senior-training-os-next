from __future__ import annotations

from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.known_skill import KnownSkill
from contracts.screen_state import ScreenState


class Planner:
    def next_action(
        self,
        objective: str,
        state: ScreenState,
        history: list[IntentAction],
        known_skills: list[KnownSkill],
    ) -> IntentAction:
        objective_l = objective.lower()

        if 'pesquisar' in objective_l or 'buscar' in objective_l:
            return IntentAction(
                intent_id='plan_search_step',
                goal_type='search',
                business_entity=self._infer_entity_from_objective(objective),
                semantic_target=self._pick_search_target(state, known_skills),
                ui_context=state.primary_area,
                expected_effect=ExpectedEffect(
                    effect_type='grid_refresh',
                    description='A lista ou grade deve ser atualizada após a pesquisa.',
                ),
                pedagogical_value='Ensina como localizar registros usando busca contextual.',
                semantic_confidence=0.72,
                reasoning_trace=['planner_rule=search_objective'],
            )

        return IntentAction(
            intent_id='plan_navigation_step',
            goal_type='navigate',
            business_entity=self._infer_entity_from_objective(objective),
            semantic_target=self._pick_navigation_target(state, known_skills),
            ui_context=state.primary_area,
            expected_effect=ExpectedEffect(
                effect_type='screen_change',
                description='A tela deve mudar para aproximar o objetivo.',
            ),
            pedagogical_value='Ensina navegação até a área correta do sistema.',
            semantic_confidence=0.65,
            reasoning_trace=['planner_rule=default_navigation'],
        )

    def _infer_entity_from_objective(self, objective: str) -> str | None:
        blob = objective.lower()
        if 'cliente' in blob:
            return 'cliente'
        if 'fornecedor' in blob:
            return 'fornecedor'
        if 'pedido' in blob:
            return 'pedido'
        if 'documento' in blob or 'ged' in blob:
            return 'documento'
        return None

    def _pick_search_target(self, state: ScreenState, skills: list[KnownSkill]) -> str:
        for skill in skills:
            if skill.goal_type == 'search':
                return skill.semantic_target
        for hint in state.visible_hints:
            label = (hint.label or '').lower()
            if any(k in label for k in ['pesquisar', 'buscar', 'filtro', 'filtrar']):
                return hint.label or 'campo de busca'
        return 'campo de busca'

    def _pick_navigation_target(self, state: ScreenState, skills: list[KnownSkill]) -> str:
        for skill in skills:
            if skill.goal_type == 'navigate':
                return skill.semantic_target
        for hint in state.visible_hints:
            if hint.kind in {'button', 'a'} and hint.label:
                return hint.label
        return 'menu principal'