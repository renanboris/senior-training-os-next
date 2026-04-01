from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass


class AuthenticationError(Exception):
    """Credenciais inválidas ou login rejeitado pelo sistema."""


class MFATimeoutError(TimeoutError):
    """Código MFA não fornecido dentro do tempo limite."""


@dataclass
class SessionConfig:
    senior_url: str
    user: str = ""
    password: str = ""
    headless: bool = False
    video_dir: str = "videos_gerados"


class SessionBootstrap:
    # Seletores do formulário de login do Senior X
    _SELECTOR_USER = "input[name='username'], input[type='text'][id*='user'], input[aria-label*='usuário' i]"
    _SELECTOR_PASS = "input[name='password'], input[type='password']"
    _SELECTOR_SUBMIT = "button[type='submit'], input[type='submit'], button:has-text('Entrar'), button:has-text('Login')"
    _SELECTOR_ERROR = ".login-error, .alert-danger, [class*='error']:visible, [class*='invalid']:visible"
    _SELECTOR_DASHBOARD = ".senior-shell, .app-root, [id='app'], nav.sidebar, .main-content"
    _SELECTOR_MFA = "input[name='mfa'], input[name='otp'], input[aria-label*='código' i], input[placeholder*='código' i]"

    def __init__(self, playwright_browser_factory) -> None:
        self.playwright_browser_factory = playwright_browser_factory

    async def start(self, cfg: SessionConfig):
        browser, context, page = await self.playwright_browser_factory(
            headless=cfg.headless,
            record_video_dir=cfg.video_dir,
        )
        return browser, context, page

    async def login(self, page, cfg: SessionConfig) -> None:
        user = os.getenv("SENIOR_USER") or cfg.user
        password = os.getenv("SENIOR_PASS") or cfg.password

        if not user or not password:
            raise AuthenticationError(
                "Credenciais ausentes. Configure SENIOR_USER e SENIOR_PASS."
            )

        await page.goto(cfg.senior_url)
        await page.wait_for_load_state("domcontentloaded", timeout=30000)

        # Preenche usuário
        await page.locator(self._SELECTOR_USER).first.fill(user)

        # Preenche senha
        await page.locator(self._SELECTOR_PASS).first.fill(password)

        # Submete
        await page.locator(self._SELECTOR_SUBMIT).first.click()

        # Aguarda resultado: dashboard, erro ou MFA
        try:
            result = await page.wait_for_selector(
                f"{self._SELECTOR_DASHBOARD}, {self._SELECTOR_ERROR}, {self._SELECTOR_MFA}",
                timeout=30000,
            )
        except Exception:
            raise TimeoutError("Login não completou dentro de 30 segundos.")

        matched = await result.evaluate("el => el.className + ' ' + (el.getAttribute('name') || '')")

        # Verifica erro de login
        error_locator = page.locator(self._SELECTOR_ERROR)
        if await error_locator.count() > 0:
            raise AuthenticationError("Login rejeitado: credenciais inválidas ou acesso negado.")

        # Verifica MFA
        mfa_locator = page.locator(self._SELECTOR_MFA)
        if await mfa_locator.count() > 0:
            await self._handle_mfa(page, mfa_locator)

        await self.wait_spa_ready(page)

    async def _handle_mfa(self, page, mfa_locator) -> None:
        mfa_code = os.getenv("SENIOR_MFA_CODE")
        if not mfa_code:
            # Aguarda até 60s por SENIOR_MFA_CODE via polling
            for _ in range(60):
                await asyncio.sleep(1)
                mfa_code = os.getenv("SENIOR_MFA_CODE")
                if mfa_code:
                    break

        if not mfa_code:
            raise MFATimeoutError(
                "Código MFA não fornecido em 60 segundos. Configure SENIOR_MFA_CODE."
            )

        await mfa_locator.first.fill(mfa_code)
        submit = page.locator(self._SELECTOR_SUBMIT)
        if await submit.count() > 0:
            await submit.first.click()

    async def wait_spa_ready(self, page, timeout_ms: int = 20000) -> None:
        await page.wait_for_load_state("networkidle", timeout=timeout_ms)
