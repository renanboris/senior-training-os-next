from __future__ import annotations

from contracts.observed_action import StateChange


class StateDiffEngine:
    def detect(self, before: dict, after: dict) -> StateChange:
        before_url = (before or {}).get("url")
        after_url = (after or {}).get("url")
        before_title = (before or {}).get("title")
        after_title = (after or {}).get("title")
        before_modal = bool((before or {}).get("modal_open", False))
        after_modal = bool((after or {}).get("modal_open", False))

        if before_url and after_url and before_url != after_url:
            return StateChange(
                changed=True,
                change_type="navigation",
                change_summary=f"Mudou de URL: {before_url} -> {after_url}",
            )

        if not before_modal and after_modal:
            return StateChange(
                changed=True,
                change_type="modal_open",
                change_summary="Um modal foi aberto após a ação.",
            )

        if before_modal and not after_modal:
            return StateChange(
                changed=True,
                change_type="modal_close",
                change_summary="O modal foi fechado após a ação.",
            )

        if before_title != after_title:
            return StateChange(
                changed=True,
                change_type="screen_change",
                change_summary=f"Título da tela mudou: {before_title} -> {after_title}",
            )

        return StateChange(
            changed=False,
            change_type="none",
            change_summary="Nenhuma mudança estrutural detectada.",
        )