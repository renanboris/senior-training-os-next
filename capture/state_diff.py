from __future__ import annotations

from contracts.observed_action import StateChange


class StateDiffEngine:
    """Detecta mudanças de estado entre dois snapshots de tela.

    Os snapshots são dicts com as chaves:
      url, title, modal_open, grid_row_count, toast_present
    (compatíveis com ScreenSnapshot.model_dump())

    Ordem de prioridade:
      navigation > modal_open > modal_close > toast > grid_refresh > title_change > none
    """

    def __init__(
        self,
        grid_selectors: list[str] | None = None,
        toast_selectors: list[str] | None = None,
    ) -> None:
        self.grid_selectors = grid_selectors or [
            "tr[data-row]",
            ".p-datatable-row",
            ".ag-row",
        ]
        self.toast_selectors = toast_selectors or [
            ".p-toast-message",
            ".toast-message",
            "[role='alert']",
        ]

    def detect(self, before: dict, after: dict) -> StateChange:
        before = before or {}
        after = after or {}

        before_url = before.get("url")
        after_url = after.get("url")
        before_title = before.get("title")
        after_title = after.get("title")
        before_modal = bool(before.get("modal_open", False))
        after_modal = bool(after.get("modal_open", False))
        before_grid = int(before.get("grid_row_count", 0))
        after_grid = int(after.get("grid_row_count", 0))
        before_toast = bool(before.get("toast_present", False))
        after_toast = bool(after.get("toast_present", False))

        # 1. navigation
        if before_url and after_url and before_url != after_url:
            return StateChange(
                changed=True,
                change_type="navigation",
                change_summary=f"Mudou de URL: {before_url} -> {after_url}",
            )

        # 2. modal_open
        if not before_modal and after_modal:
            return StateChange(
                changed=True,
                change_type="modal_open",
                change_summary="Um modal foi aberto após a ação.",
            )

        # 3. modal_close
        if before_modal and not after_modal:
            return StateChange(
                changed=True,
                change_type="modal_close",
                change_summary="O modal foi fechado após a ação.",
            )

        # 4. toast
        if not before_toast and after_toast:
            return StateChange(
                changed=True,
                change_type="toast",
                change_summary="Uma notificação (toast) apareceu após a ação.",
            )

        # 5. grid_refresh
        if before_grid != after_grid:
            return StateChange(
                changed=True,
                change_type="grid_refresh",
                change_summary=f"Grade atualizada: {before_grid} → {after_grid} linhas.",
            )

        # 6. title_change
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
