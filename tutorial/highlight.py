from __future__ import annotations

from typing import Optional

from contracts.observed_action import RelativeBox
from runtime.ui_overlays import safe_evaluate

_HIGHLIGHT_ID = "senior-element-highlight"


class ElementHighlight:
    """Injeta e remove um highlight visual sobre o elemento-alvo via JavaScript."""

    HIGHLIGHT_COLOR = "#FF6B35"
    Z_INDEX = 2147483644

    def _build_inject_script(
        self,
        x_pct: float,
        y_pct: float,
        w_pct: float,
        h_pct: float,
    ) -> str:
        return f"""() => {{
            const existing = document.getElementById('{_HIGHLIGHT_ID}');
            if (existing) existing.remove();
            const x = {x_pct} * window.innerWidth;
            const y = {y_pct} * window.innerHeight;
            const w = {w_pct} * window.innerWidth;
            const h = {h_pct} * window.innerHeight;
            const el = document.createElement('div');
            el.id = '{_HIGHLIGHT_ID}';
            el.style.cssText = [
                'position:fixed',
                'pointer-events:none',
                'left:' + x + 'px',
                'top:' + y + 'px',
                'width:' + w + 'px',
                'height:' + h + 'px',
                'border:3px solid {self.HIGHLIGHT_COLOR}',
                'border-radius:4px',
                'box-shadow:0 0 0 4px rgba(255,107,53,0.3)',
                'z-index:{self.Z_INDEX}',
                'transition:all 0.2s ease',
            ].join(';');
            document.documentElement.appendChild(el);
        }}"""

    async def inject(
        self,
        page_or_frame,
        coords_rel: Optional[RelativeBox] = None,
        selector: Optional[str] = None,
    ) -> None:
        """Injeta o highlight. Usa coords_rel se disponível, senão tenta via selector."""
        if coords_rel is not None:
            script = self._build_inject_script(
                coords_rel.x_pct,
                coords_rel.y_pct,
                coords_rel.w_pct,
                coords_rel.h_pct,
            )
            try:
                await page_or_frame.evaluate(script)
            except Exception:
                pass
        elif selector:
            bbox_script = f"""() => {{
                const el = document.querySelector('{selector}');
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return {{
                    x_pct: r.left / window.innerWidth,
                    y_pct: r.top / window.innerHeight,
                    w_pct: r.width / window.innerWidth,
                    h_pct: r.height / window.innerHeight,
                }};
            }}"""
            try:
                bbox = await page_or_frame.evaluate(bbox_script)
                if bbox:
                    script = self._build_inject_script(
                        bbox["x_pct"], bbox["y_pct"], bbox["w_pct"], bbox["h_pct"]
                    )
                    await page_or_frame.evaluate(script)
            except Exception:
                pass
        # Se nem coords_rel nem selector: não injeta (sem erro)

    async def remove(self, page_or_frame) -> None:
        """Remove o highlight do DOM."""
        try:
            await page_or_frame.evaluate(
                f"() => {{ const e = document.getElementById('{_HIGHLIGHT_ID}'); if (e) e.remove(); }}"
            )
        except Exception:
            pass
