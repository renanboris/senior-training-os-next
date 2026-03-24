from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SessionConfig:
    senior_url: str
    user: str
    password: str
    headless: bool = False
    video_dir: str = "videos_gerados"


class SessionBootstrap:
    def __init__(self, playwright_browser_factory):
        self.playwright_browser_factory = playwright_browser_factory

    async def start(self, cfg: SessionConfig):
        browser, context, page = await self.playwright_browser_factory(
            headless=cfg.headless,
            record_video_dir=cfg.video_dir,
        )
        return browser, context, page

    async def login(self, page, cfg: SessionConfig) -> None:
        await page.goto(cfg.senior_url)

        user = os.getenv("SENIOR_USER", cfg.user)
        password = os.getenv("SENIOR_PASS", cfg.password)

        if not user or not password:
            raise RuntimeError("Credenciais do Senior X ausentes para login automático.")

        # Placeholder simples. O login real continua no legado até migrarmos por inteiro.
        await page.wait_for_load_state("domcontentloaded")

    async def wait_spa_ready(self, page, timeout_ms: int = 20000) -> None:
        await page.wait_for_load_state("networkidle", timeout=timeout_ms)