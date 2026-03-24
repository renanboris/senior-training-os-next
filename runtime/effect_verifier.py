from __future__ import annotations

from contracts.intent_action import IntentAction
from contracts.observed_action import ScreenSnapshot


class EffectVerifier:
    def verify(self, intent: IntentAction, before: ScreenSnapshot, after: ScreenSnapshot) -> tuple[bool, str]:
        if before.url != after.url:
            return True, "URL mudou após a ação."

        if intent.expected_effect.effect_type == "modal_open" and (not before.modal_open and after.modal_open):
            return True, "Modal abriu conforme esperado."

        if intent.expected_effect.effect_type == "modal_close" and (before.modal_open and not after.modal_open):
            return True, "Modal fechou conforme esperado."

        if before.title != after.title:
            return True, "Título da tela mudou após a ação."

        return False, "Nenhuma evidência forte de efeito detectada."