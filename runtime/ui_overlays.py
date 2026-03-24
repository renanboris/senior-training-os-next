from __future__ import annotations

import asyncio


async def safe_evaluate(target, script: str, arg=None, timeout: float = 3.0) -> bool:
    try:
        coro = target.evaluate(script, arg) if arg is not None else target.evaluate(script)
        await asyncio.wait_for(coro, timeout=timeout)
        return True
    except Exception:
        return False


async def update_progress_pill(page, current_step: int, total_steps: int, lesson_name: str) -> None:
    pct = int((current_step / max(total_steps, 1)) * 100)
    dashoffset = 62.8 - (62.8 * pct) / 100
    script = f"""() => {{
        let pill = document.getElementById('senior-progress-pill');
        if (!pill) {{
            pill = document.createElement('div');
            pill.id = 'senior-progress-pill';
            pill.style.cssText = 'position:fixed;bottom:30px;right:30px;z-index:2147483646;background:rgba(15,23,42,.85);padding:10px 20px;border-radius:100px;color:#fff;font-family:Segoe UI,sans-serif;';
            pill.innerHTML = `<div id="senior-progress-step"></div><svg width="24" height="24"><circle id="senior-progress-circle" r="10" cx="12" cy="12" stroke="white" stroke-width="3" fill="transparent" stroke-dasharray="62.8" stroke-dashoffset="62.8"></circle></svg>`;
            document.documentElement.appendChild(pill);
        }}
        const circle = document.getElementById('senior-progress-circle');
        const step = document.getElementById('senior-progress-step');
        if (circle) circle.style.strokeDashoffset = '{dashoffset}';
        if (step) step.innerText = '{lesson_name} — Passo {current_step} de {total_steps}';
    }}"""
    await safe_evaluate(page, script)


async def show_subtitle(page, text: str) -> None:
    if not text or not text.strip():
        return
    script = """(texto) => {
        const current = document.getElementById('senior-video-subtitle');
        if (current) current.remove();
        const sub = document.createElement('div');
        sub.id = 'senior-video-subtitle';
        sub.style.cssText = 'position:fixed;bottom:40px;left:50%;transform:translateX(-50%);background:rgba(15,23,42,.85);color:#fff;padding:12px 30px;border-radius:50px;z-index:2147483645;font-family:Segoe UI,sans-serif;max-width:75%;';
        sub.innerHTML = texto;
        document.documentElement.appendChild(sub);
    }"""
    await safe_evaluate(page, script, arg=text)


async def remove_subtitle(page) -> None:
    await safe_evaluate(page, "() => { const e = document.getElementById('senior-video-subtitle'); if (e) e.remove(); }")