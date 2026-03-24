from __future__ import annotations

from contracts.screen_state import ScreenState, VisibleElementHint


class ScreenObserver:
    async def observe(self, page) -> ScreenState:
        title = await page.title()
        url = page.url
        frame_count = len(page.frames)

        modal_open = await page.evaluate(
            """
            () => Boolean(
                document.querySelector('.p-dialog-mask, .cdk-overlay-pane, [role="dialog"], .modal, .mat-dialog-container')
            )
            """
        )

        visible_text_excerpt = await page.evaluate(
            """
            () => {
                const text = document.body && document.body.innerText ? document.body.innerText : '';
                return text.split('
').join(' ').split('  ').join(' ').trim().slice(0, 1200);
            }
            """
        )

        active_element_label = await page.evaluate(
            """
            () => {
                const el = document.activeElement;
                if (!el) return null;
                return el.getAttribute('aria-label') || el.getAttribute('name') || el.getAttribute('placeholder') || el.innerText || null;
            }
            """
        )

        raw_hints = await page.evaluate(
            """
            () => {
                const selectors = 'button, input, a, [role="button"], [role="tab"], label';
                const nodes = Array.from(document.querySelectorAll(selectors))
                    .slice(0, 30)
                    .map(el => ({
                        kind: (el.tagName || '').toLowerCase(),
                        label: ((el.innerText || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim()).slice(0, 80),
                        role: el.getAttribute('role') || null,
                    }))
                    .filter(x => x.label);
                return nodes;
            }
            """
        )

        if not isinstance(raw_hints, list):
            raw_hints = []

        hints = [VisibleElementHint(**item) for item in raw_hints if isinstance(item, dict)]
        fingerprint = self._build_fingerprint(url, title, modal_open, hints)

        return ScreenState(
            url=url,
            title=title,
            fingerprint=fingerprint,
            frame_count=frame_count,
            active_element_label=active_element_label,
            modal_open=modal_open,
            visible_text_excerpt=visible_text_excerpt,
            primary_area=self._infer_primary_area(url, title, visible_text_excerpt),
            visible_hints=hints,
        )

    def _build_fingerprint(self, url: str | None, title: str | None, modal_open: bool, hints: list[VisibleElementHint]) -> str:
        first_hints = '|'.join((h.label or '')[:20] for h in hints[:5])
        return f"{url or 'no_url'}::{title or 'no_title'}::modal={int(modal_open)}::{first_hints}"

    def _infer_primary_area(self, url: str | None, title: str | None, text: str | None) -> str | None:
        blob = f"{url or ''} {title or ''} {text or ''}".lower()
        if 'ged' in blob:
            return 'ged'
        if 'cadastro' in blob:
            return 'cadastro'
        if 'financeiro' in blob:
            return 'financeiro'
        if 'pedido' in blob:
            return 'pedido'
        return None