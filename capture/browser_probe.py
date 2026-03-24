from __future__ import annotations

from pathlib import Path
from typing import Any


class BrowserProbe:
    def __init__(self, script: str):
        self.script = script

    async def inject(self, page) -> None:
        await page.evaluate(self.script)

    async def snapshot_screen(self, page) -> dict[str, Any]:
        return {
            "url": page.url,
            "title": await page.title(),
            "frame_count": len(page.frames),
            "modal_open": await page.evaluate(
                """
                () => !!document.querySelector(
                    '.p-dialog-mask, .cdk-overlay-pane, [role="dialog"], .modal, .mat-dialog-container'
                )
                """
            ),
        }

    async def save_screenshot(self, page, path: str) -> str:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(output), type="jpeg", quality=70)
        return str(output)