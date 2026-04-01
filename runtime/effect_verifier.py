from __future__ import annotations

from typing import Optional

from contracts.intent_action import IntentAction
from contracts.observed_action import ScreenSnapshot, StateChange


class EffectVerifier:
    """Verifica se o efeito esperado de uma ação ocorreu.

    Aceita um StateChange opcional para desacoplar detecção de verificação.
    Quando state_change é fornecido, usa diretamente; caso contrário, deriva
    da comparação entre before e after.
    """

    def verify(
        self,
        intent: IntentAction,
        before: ScreenSnapshot,
        after: ScreenSnapshot,
        state_change: Optional[StateChange] = None,
    ) -> tuple[bool, str]:
        # Deriva StateChange se não fornecido
        if state_change is None:
            state_change = self._derive_state_change(before, after)

        effect = intent.expected_effect.effect_type

        # grid_refresh
        if effect == "grid_refresh" and state_change.change_type == "grid_refresh":
            return True, "Grade atualizada conforme esperado."

        # toast_visible
        if effect == "toast_visible" and state_change.change_type == "toast":
            return True, "Notificação (toast) exibida conforme esperado."

        # navigation / screen_change
        if effect == "screen_change" and state_change.change_type in {"navigation", "screen_change"}:
            return True, state_change.change_summary or "Tela mudou conforme esperado."

        # modal_open
        if effect == "modal_open" and state_change.change_type == "modal_open":
            return True, "Modal abriu conforme esperado."

        # modal_close
        if effect == "modal_close" and state_change.change_type == "modal_close":
            return True, "Modal fechou conforme esperado."

        # field_filled — qualquer mudança detectada é suficiente
        if effect == "field_filled" and state_change.changed:
            return True, "Campo preenchido e mudança detectada."

        # Fallback: verifica URL e título diretamente
        if before.url != after.url:
            return True, "URL mudou após a ação."
        if before.title != after.title:
            return True, "Título da tela mudou após a ação."

        return False, "Nenhuma evidência forte de efeito detectada."

    def _derive_state_change(
        self, before: ScreenSnapshot, after: ScreenSnapshot
    ) -> StateChange:
        """Deriva um StateChange básico comparando dois ScreenSnapshots."""
        if before.url != after.url:
            return StateChange(
                changed=True,
                change_type="navigation",
                change_summary=f"URL mudou: {before.url} → {after.url}",
            )
        if not before.modal_open and after.modal_open:
            return StateChange(changed=True, change_type="modal_open")
        if before.modal_open and not after.modal_open:
            return StateChange(changed=True, change_type="modal_close")
        if not before.toast_present and after.toast_present:
            return StateChange(changed=True, change_type="toast")
        if before.grid_row_count != after.grid_row_count:
            return StateChange(changed=True, change_type="grid_refresh")
        if before.title != after.title:
            return StateChange(changed=True, change_type="screen_change")
        return StateChange(changed=False, change_type="none")
