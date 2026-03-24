from __future__ import annotations

from contracts.observed_action import ObservedAction
from contracts.screen_state import ScreenState


class PromptBuilder:
    def build_intent_prompt(self, observed: ObservedAction, state: ScreenState) -> str:
        return f"""
Você é um intérprete semântico de ações corporativas.

Ação observada:
- tipo: {observed.action_type}
- texto alvo: {observed.raw_target.text}
- aria-label: {observed.raw_target.aria_label}
- valor digitado: {observed.typed_value}
- mudança detectada: {observed.state_change.change_type if observed.state_change else 'none'}

Tela atual:
- url: {state.url}
- título: {state.title}
- área principal: {state.primary_area}
- hints visíveis: {[h.label for h in state.visible_hints[:10]]}

Responda com:
1. intenção principal
2. entidade de negócio
3. efeito esperado
4. valor pedagógico
""".strip()