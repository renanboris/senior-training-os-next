"""Script de debug para inspecionar o fluxo de login do Senior X SSO."""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Carrega .env
_env_path = ROOT / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        _k = _k.strip()
        _v = _v.strip().strip('"').strip("'")
        if _k and _k not in os.environ:
            os.environ[_k] = _v

SENIOR_URL = os.getenv(
    "SENIOR_URL",
    "https://platform-homologx.senior.com.br/tecnologia/platform/senior-x/#/",
)
USER = os.getenv("SENIOR_USER", "")
PASS = os.getenv("SENIOR_PASS", "")


async def main():
    from playwright.async_api import async_playwright

    print(f"URL: {SENIOR_URL}")
    print(f"User: {USER}")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()

        print("=== PASSO 1: Abrindo URL inicial ===")
        await page.goto(SENIOR_URL)
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        print(f"URL apos goto: {page.url}")

        # Inspeciona todos os inputs visiveis
        inputs = await page.evaluate("""
            () => Array.from(document.querySelectorAll('input')).map(el => ({
                type: el.type,
                name: el.name,
                id: el.id,
                placeholder: el.placeholder,
                visible: el.offsetParent !== null,
                value: el.value ? '[preenchido]' : ''
            }))
        """)
        print(f"Inputs encontrados: {len(inputs)}")
        for inp in inputs:
            print(f"  type={inp['type']:10s} name={inp['name']:20s} id={inp['id']:20s} visible={inp['visible']}")

        # Inspeciona botoes
        buttons = await page.evaluate("""
            () => Array.from(document.querySelectorAll('button, input[type=submit]')).map(el => ({
                type: el.type || el.tagName,
                text: (el.innerText || el.value || '').trim().slice(0, 50),
                id: el.id,
                visible: el.offsetParent !== null
            }))
        """)
        print(f"\nBotoes encontrados: {len(buttons)}")
        for btn in buttons:
            print(f"  type={btn['type']:10s} id={btn['id']:20s} text={btn['text']}")

        print("\n=== PASSO 2: Preenchendo email ===")
        await page.locator("input#username-input-field, input[type='email']").first.fill(USER)
        print("  Email preenchido")

        print("\n=== PASSO 3: Clicando nextBtn ===")
        await page.locator("button#nextBtn").click()
        print("  nextBtn clicado")

        print("\n=== PASSO 4: Aguardando campo de senha ficar visivel ===")
        await page.locator("input#password-input-field").wait_for(state="visible", timeout=15000)
        print("  Campo de senha visivel!")

        print("\n=== PASSO 5: Preenchendo senha ===")
        await page.locator("input#password-input-field").fill(PASS)
        print("  Senha preenchida")

        print("\n=== PASSO 6: Clicando loginbtn ===")
        await page.locator("button#loginbtn").click()
        print("  loginbtn clicado")

        print("\nAguardando redirect...")
        try:
            await page.wait_for_url(
                lambda url: "login" not in url and "sso" not in url,
                timeout=30000,
            )
        except Exception as e:
            print(f"wait_for_url: {e}")

        await page.wait_for_load_state("networkidle", timeout=20000)
        print(f"\nURL final: {page.url}")
        print("Login OK!" if "login" not in page.url else "Ainda na tela de login")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
