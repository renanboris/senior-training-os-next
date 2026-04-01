from __future__ import annotations

from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.known_skill import KnownSkill
from contracts.screen_state import ScreenState
from cil.entity_utils import infer_business_entity

_LOOP_THRESHOLD = 3  # repetições consecutivas do mesmo target para detectar loop


class Planner:
    def next_action(
        self,
        objective: str,
        state: ScreenState,
        history: list[IntentAction],
        known_skills: list[KnownSkill],
    ) -> IntentAction:
        # 1. Detecta loop
        if self._detect_loop(history):
            alt_target = self._pick_alternative_target(state, history, known_skills)
            return IntentAction(
                intent_id="plan_loop_escape",
                goal_type="navigate",
                business_entity=infer_business_entity(objective),
                semantic_target=alt_target,
                ui_context=state.primary_area,
                expected_effect=ExpectedEffect(
                    effect_type="screen_change",
                    description="Navegação alternativa para escapar de loop.",
                ),
                pedagogical_value="Ensina como navegar para uma área diferente quando o sistema está em loop.",
                semantic_confidence=0.55,
                reasoning_trace=["loop_detected", f"alternative_target={alt_target}"],
            )

        objective_l = objective.lower()
        entity = infer_business_entity(objective)

        # 2. Prioriza known_skills de maior confidence quando disponíveis
        best_skill = self._best_skill_for_objective(objective_l, known_skills)

        # 3. Regras por goal_type (7+ regras)
        if any(k in objective_l for k in ["pesquisar", "buscar", "filtrar", "procurar"]):
            return self._make_intent(
                "plan_search",
                "search",
                entity,
                best_skill.semantic_target if best_skill and best_skill.goal_type == "search"
                else self._pick_search_target(state, known_skills),
                state,
                "grid_refresh",
                "A lista ou grade deve ser atualizada após a pesquisa.",
                "Ensina como localizar registros usando busca contextual.",
                0.72,
                ["planner_rule=search_objective"],
            )

        if any(k in objective_l for k in ["preencher", "digitar", "inserir", "informar"]):
            return self._make_intent(
                "plan_fill",
                "fill",
                entity,
                best_skill.semantic_target if best_skill and best_skill.goal_type == "fill"
                else self._pick_target_from_hints(state, known_skills, "fill", "campo"),
                state,
                "field_filled",
                "O campo deve ser preenchido corretamente.",
                "Ensina como preencher campos de formulário.",
                0.68,
                ["planner_rule=fill_objective"],
            )

        if any(k in objective_l for k in ["confirmar", "confirme", "aceitar", "aprovar"]):
            return self._make_intent(
                "plan_confirm",
                "confirm",
                entity,
                best_skill.semantic_target if best_skill and best_skill.goal_type == "confirm"
                else "Confirmar",
                state,
                "modal_close",
                "O modal de confirmação deve fechar.",
                "Ensina como confirmar uma operação.",
                0.75,
                ["planner_rule=confirm_objective"],
            )

        if any(k in objective_l for k in ["salvar", "gravar", "registrar"]):
            return self._make_intent(
                "plan_save",
                "save",
                entity,
                best_skill.semantic_target if best_skill and best_skill.goal_type == "save"
                else "Salvar",
                state,
                "record_saved",
                "O registro deve ser salvo.",
                "Ensina como salvar um registro.",
                0.70,
                ["planner_rule=save_objective"],
            )

        if any(k in objective_l for k in ["abrir", "visualizar", "detalhar", "ver"]):
            return self._make_intent(
                "plan_open",
                "open",
                entity,
                best_skill.semantic_target if best_skill and best_skill.goal_type == "open"
                else self._pick_target_from_hints(state, known_skills, "open", "item"),
                state,
                "modal_open",
                "Um modal ou detalhe deve abrir.",
                "Ensina como abrir um registro para visualização.",
                0.68,
                ["planner_rule=open_objective"],
            )

        if any(k in objective_l for k in ["selecionar", "escolher", "marcar"]):
            return self._make_intent(
                "plan_select",
                "select",
                entity,
                best_skill.semantic_target if best_skill and best_skill.goal_type == "select"
                else self._pick_target_from_hints(state, known_skills, "select", "opção"),
                state,
                "field_filled",
                "A opção deve ser selecionada.",
                "Ensina como selecionar uma opção.",
                0.65,
                ["planner_rule=select_objective"],
            )

        if any(k in objective_l for k in ["excluir", "remover", "apagar", "deletar"]):
            return self._make_intent(
                "plan_delete",
                "delete",
                entity,
                best_skill.semantic_target if best_skill and best_skill.goal_type == "delete"
                else "Excluir",
                state,
                "screen_change",
                "O registro deve ser removido.",
                "Ensina como excluir um registro.",
                0.65,
                ["planner_rule=delete_objective"],
            )

        if any(k in objective_l for k in ["filtrar", "filtro", "aplicar filtro"]):
            return self._make_intent(
                "plan_filter",
                "filter",
                entity,
                best_skill.semantic_target if best_skill and best_skill.goal_type == "filter"
                else self._pick_target_from_hints(state, known_skills, "filter", "filtro"),
                state,
                "grid_refresh",
                "A grade deve ser filtrada.",
                "Ensina como aplicar filtros.",
                0.65,
                ["planner_rule=filter_objective"],
            )

        # Fallback: navigate
        return self._make_intent(
            "plan_navigate",
            "navigate",
            entity,
            best_skill.semantic_target if best_skill and best_skill.goal_type == "navigate"
            else self._pick_navigation_target(state, known_skills),
            state,
            "screen_change",
            "A tela deve mudar para aproximar o objetivo.",
            "Ensina navegação até a área correta do sistema.",
            0.60,
            ["planner_rule=default_navigation"],
        )

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _detect_loop(self, history: list[IntentAction]) -> bool:
        if len(history) < _LOOP_THRESHOLD:
            return False
        last = history[-_LOOP_THRESHOLD:]
        targets = [a.semantic_target for a in last]
        return len(set(targets)) == 1

    def _pick_alternative_target(
        self,
        state: ScreenState,
        history: list[IntentAction],
        known_skills: list[KnownSkill],
    ) -> str:
        recent_targets = {a.semantic_target for a in history[-_LOOP_THRESHOLD:]}
        for skill in sorted(known_skills, key=lambda s: s.confidence, reverse=True):
            if skill.semantic_target not in recent_targets:
                return skill.semantic_target
        for hint in state.visible_hints:
            if hint.label and hint.label not in recent_targets:
                return hint.label
        return "menu principal"

    def _best_skill_for_objective(
        self, objective_l: str, skills: list[KnownSkill]
    ) -> KnownSkill | None:
        candidates = [s for s in skills if s.goal_type in objective_l or True]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.confidence)

    def _pick_search_target(self, state: ScreenState, skills: list[KnownSkill]) -> str:
        for skill in skills:
            if skill.goal_type == "search":
                return skill.semantic_target
        for hint in state.visible_hints:
            label = (hint.label or "").lower()
            if any(k in label for k in ["pesquisar", "buscar", "filtro", "filtrar"]):
                return hint.label or "campo de busca"
        return "campo de busca"

    def _pick_navigation_target(self, state: ScreenState, skills: list[KnownSkill]) -> str:
        for skill in skills:
            if skill.goal_type == "navigate":
                return skill.semantic_target
        for hint in state.visible_hints:
            if hint.kind in {"button", "a"} and hint.label:
                return hint.label
        return "menu principal"

    def _pick_target_from_hints(
        self,
        state: ScreenState,
        skills: list[KnownSkill],
        goal_type: str,
        fallback: str,
    ) -> str:
        for skill in skills:
            if skill.goal_type == goal_type:
                return skill.semantic_target
        for hint in state.visible_hints:
            if hint.label:
                return hint.label
        return fallback

    def _make_intent(
        self,
        intent_id: str,
        goal_type: str,
        entity: str | None,
        semantic_target: str,
        state: ScreenState,
        effect_type: str,
        effect_desc: str,
        pedagogical_value: str,
        confidence: float,
        trace: list[str],
    ) -> IntentAction:
        return IntentAction(
            intent_id=intent_id,
            goal_type=goal_type,
            business_entity=entity,
            semantic_target=semantic_target,
            ui_context=state.primary_area,
            expected_effect=ExpectedEffect(
                effect_type=effect_type,
                description=effect_desc,
            ),
            pedagogical_value=pedagogical_value,
            semantic_confidence=confidence,
            reasoning_trace=trace,
        )
