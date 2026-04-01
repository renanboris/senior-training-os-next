"""Shadow Mode Homologation Runner.

Uso (Windows PowerShell):
    py scripts/run_shadow_homolog.py shadow_exports/TESTE_DUAL_002_shadow.jsonl --dry-run
    py scripts/run_shadow_homolog.py shadow_exports/TESTE_DUAL_002_shadow.jsonl
    py scripts/run_shadow_homolog.py shadow_exports/TESTE_DUAL_002_shadow.jsonl --headless
    py scripts/run_shadow_homolog.py shadow_exports/TESTE_DUAL_002_shadow.jsonl --dry-run --max-events 5

Modos:
  --dry-run   Sem browser. Usa mocks + coordenadas do shadow.jsonl.
              Valida o pipeline semantico sem conexao com o Senior X.
  (padrao)    Abre browser visivel, faz login SSO automatico, observa
              o estado real da tela para cada evento. NAO executa acoes.
  --headless  Igual ao padrao, mas sem janela visivel.
  --max-events N  Limita o numero de eventos processados.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

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

_cli = sys.argv[1:]
# Args CLI tem prioridade absoluta sobre env vars
# Padrao sem flags: LIVE (com browser)
if "--live" in _cli:
    DRY_RUN = False
    HEADLESS = "--headless" in _cli
elif "--dry-run" in _cli:
    DRY_RUN = True
    HEADLESS = "--headless" in _cli
elif "--headless" in _cli:
    DRY_RUN = False
    HEADLESS = True
else:
    # Sem flags CLI: usa env var, mas padrao e LIVE (False)
    DRY_RUN = os.getenv("DRY_RUN", "0") in {"1", "true", "yes"}
    HEADLESS = os.getenv("HEADLESS", "0") in {"1", "true", "yes"}
_mi = next((i for i, a in enumerate(_cli) if a == "--max-events"), None)
MAX_EVENTS = int(_cli[_mi + 1]) if _mi is not None and _mi + 1 < len(_cli) else int(os.getenv("MAX_EVENTS", "0"))
SKILLS_PATH = ROOT / "data" / "homolog" / "skills.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _print(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def _sep(char: str = "-", width: int = 72) -> None:
    print(char * width, flush=True)


def _infer_area(fp: str) -> str | None:
    f = fp.lower()
    if "ged" in f:
        return "ged"
    if "financeiro" in f:
        return "financeiro"
    if "cadastro" in f:
        return "cadastro"
    if "pedido" in f:
        return "pedido"
    return None


def _load_events(path: Path) -> list[dict]:
    from capture.shadow_ingestion import filter_useful_events, load_jsonl
    events = load_jsonl(path)
    useful = filter_useful_events(events)
    _print(f"Shadow: {len(events)} eventos totais -> {len(useful)} uteis")
    return useful


def _to_observed(event: dict):
    from contracts.observed_action import ObservedAction, RawTarget, RelativeBox, ScreenSnapshot
    el = event.get("elemento_alvo") or {}
    ctx = (event.get("contexto_semantico") or {}).get("tela_atual") or {}
    acao = (event.get("acao") or "clique").lower()
    amap = {
        "clique": "click", "duplo_clique": "double_click",
        "digitar": "type", "digitar_e_enter": "type_and_enter",
        "selecionar": "select_option", "hover": "hover", "upload": "upload",
    }
    action_type = amap.get(acao, "click")
    cr = el.get("coordenadas_relativas") or {}
    coords_rel = None
    if cr:
        try:
            coords_rel = RelativeBox(
                x_pct=float(cr.get("x_pct", 0.5)),
                y_pct=float(cr.get("y_pct", 0.5)),
                w_pct=float(cr.get("w_pct", 0.05)),
                h_pct=float(cr.get("h_pct", 0.05)),
            )
        except Exception:
            pass
    raw_target = RawTarget(
        selector=el.get("seletor_hint"),
        tag=el.get("tipo_elemento"),
        text=event.get("business_target") or el.get("label_curto"),
        aria_label=el.get("label_curto"),
        iframe_hint=el.get("iframe_hint"),
        coords_rel=coords_rel,
    )
    cmap = {"alta": 0.9, "media": 0.7, "baixa": 0.45}
    conf = cmap.get((el.get("confianca_captura") or "media").lower(), 0.7)
    return ObservedAction(
        event_id=f"shadow_{event.get('id_acao', uuid4().hex[:8])}",
        timestamp=datetime.now(timezone.utc),
        action_type=action_type,
        raw_target=raw_target,
        typed_value=event.get("valor_input") or None,
        screen_before=__import__("contracts.observed_action", fromlist=["ScreenSnapshot"]).ScreenSnapshot(
            url=ctx.get("url"), title=ctx.get("tela_id"), fingerprint=ctx.get("tela_id"),
        ),
        capture_confidence=conf,
        risk_class="low",
    )


def _coord_map(events: list[dict]) -> dict:
    m: dict[str, dict] = {}
    for ev in events:
        el = ev.get("elemento_alvo") or {}
        t = (ev.get("business_target") or el.get("label_curto") or "").strip()
        c = el.get("coordenadas_relativas")
        if t and c:
            m[t.lower()] = c
    return m


async def _run_dry(events: list[dict], skill_memory) -> list[dict]:
    from cil.interpreter import IntentInterpreter
    from cil.policy import PolicyEngine
    from capture.shadow_ingestion import normalize_fingerprint
    from contracts.screen_state import ScreenState
    from vision.resolver import TargetResolver
    from vision.strategies.dom_strategy import DomStrategy
    from vision.strategies.coordinate_strategy import CoordinateStrategy
    from vision.strategies.base import ResolutionContext
    from unittest.mock import AsyncMock, MagicMock

    interpreter = IntentInterpreter()
    policy = PolicyEngine()

    lm = AsyncMock()
    lm.count = AsyncMock(return_value=0)
    pm = MagicMock()
    pm.get_by_role = MagicMock(return_value=lm)
    pm.get_by_label = MagicMock(return_value=lm)
    pm.get_by_placeholder = MagicMock(return_value=lm)

    cmap = _coord_map(events)
    resolver = TargetResolver(strategies=[
        DomStrategy(),
        CoordinateStrategy(coordinate_lookup=lambda t: cmap.get(t.lower())),
    ])

    records: list[dict] = []
    for idx, event in enumerate(events, 1):
        try:
            obs = _to_observed(event)
            fp = normalize_fingerprint(event)
            state = ScreenState(
                url=obs.screen_before.url,
                title=obs.screen_before.title,
                fingerprint=fp,
                primary_area=_infer_area(fp),
            )
            intent = interpreter.interpret(obs, state)
            risk = policy.evaluate(intent)
            skills = skill_memory.retrieve(state, intent)
            ctx = ResolutionContext(intent=intent, screen_state=state, known_skills=[s.model_dump() for s in skills])
            try:
                resolved, trace = await resolver.resolve(pm, ctx)
                ok = True
            except RuntimeError:
                resolved = None
                trace = type("T", (), {"steps": ["all_strategies_failed"]})()
                ok = False
            records.append({
                "event_id": obs.event_id, "step": idx,
                "intent": intent.model_dump(), "risk": risk.model_dump(),
                "resolved": resolved.model_dump() if resolved else None,
                "resolution_ok": ok, "trace": trace.steps, "skills_matched": len(skills),
            })
            st = "OK" if ok else "XX"
            strat = resolved.strategy_used if resolved else "none"
            _print(f"  [{idx:02d}] {st} {intent.goal_type:10s} | {intent.semantic_target[:35]:35s} | {strat:12s} | conf={intent.semantic_confidence:.2f}")
        except Exception as exc:
            _print(f"  [{idx:02d}] ERRO: {exc}")
            records.append({"event_id": f"err_{idx}", "error": str(exc)})
    return records


async def _run_live(events: list[dict], skill_memory) -> list[dict]:
    from playwright.async_api import async_playwright
    from cil.interpreter import IntentInterpreter
    from cil.observer import ScreenObserver
    from cil.policy import PolicyEngine
    from vision.resolver import TargetResolver
    from vision.strategies.active_element_strategy import ActiveElementStrategy
    from vision.strategies.dom_strategy import DomStrategy
    from vision.strategies.frame_strategy import FrameStrategy
    from vision.strategies.coordinate_strategy import CoordinateStrategy
    from vision.strategies.base import ResolutionContext

    interpreter = IntentInterpreter()
    observer = ScreenObserver()
    policy = PolicyEngine()
    cmap = _coord_map(events)
    resolver = TargetResolver(strategies=[
        ActiveElementStrategy(),
        DomStrategy(),
        FrameStrategy(),
        CoordinateStrategy(coordinate_lookup=lambda t: cmap.get(t.lower())),
    ])

    records: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS)
        ctx_opts = {"viewport": {"width": 1440, "height": 900}}
        if not HEADLESS:
            vid_dir = str(ROOT / "runtime_artifacts" / "homolog_videos")
            Path(vid_dir).mkdir(parents=True, exist_ok=True)
            ctx_opts["record_video_dir"] = vid_dir
        context = await browser.new_context(**ctx_opts)
        page = await context.new_page()

        # --- Login SSO Senior X (fluxo em 2 etapas) ---
        # Etapa 1: preenche email + clica nextBtn
        # Etapa 2: preenche senha + clica loginbtn
        _print("Fazendo login no Senior X (SSO)...")
        try:
            user = os.getenv("SENIOR_USER", "")
            pwd = os.getenv("SENIOR_PASS", "")
            if not user or not pwd:
                raise RuntimeError("SENIOR_USER e SENIOR_PASS nao configurados.")

            await page.goto(SENIOR_URL)
            await page.wait_for_load_state("domcontentloaded", timeout=30000)

            # Etapa 1: preenche email
            await page.locator("input#username-input-field, input[type='email']").first.fill(user)
            _print("  Email preenchido")

            # Clica no botao "Proximo" (nextBtn) para revelar o campo de senha
            # Usa force=True pois o botao pode estar parcialmente fora do viewport
            await page.locator("button#nextBtn").click(force=True)
            _print("  nextBtn clicado")

            # Aguarda a transicao CSS (o campo de senha usa animacao para aparecer)
            await asyncio.sleep(2.0)

            # Preenche senha diretamente pelo id, sem esperar visibilidade
            # (o campo existe no DOM mas pode estar em transicao CSS)
            await page.evaluate(
                """(pwd) => {
                    const el = document.getElementById('password-input-field');
                    if (el) {
                        el.removeAttribute('hidden');
                        el.style.display = '';
                        el.style.visibility = 'visible';
                        el.style.opacity = '1';
                        el.value = pwd;
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }""",
                pwd,
            )
            _print("  Senha preenchida via JS")

            # Clica no botao de login (loginbtn) via JS para garantir
            await page.evaluate(
                """() => {
                    const btn = document.getElementById('loginbtn');
                    if (btn) {
                        btn.removeAttribute('hidden');
                        btn.classList.remove('hidden');
                        btn.style.display = '';
                        btn.click();
                    }
                }"""
            )
            _print("  loginbtn clicado via JS")

            # Aguarda redirect de volta para o Senior X
            _print("  Aguardando redirect pos-login...")
            try:
                await page.wait_for_url(
                    lambda url: "login" not in url and "sso" not in url and "openid-connect" not in url,
                    timeout=45000,
                )
            except Exception:
                pass
            await page.wait_for_load_state("networkidle", timeout=30000)
            _print(f"Login OK -> {page.url[:80]}")

        except Exception as exc:
            _print(f"ERRO no login: {exc}")
            await browser.close()
            return []

        _print(f"Processando {len(events)} eventos em shadow mode...")
        _sep()

        for idx, event in enumerate(events, 1):
            try:
                obs = _to_observed(event)

                # Navega para a URL do evento antes de observar
                event_url = (
                    (event.get("contexto_semantico") or {})
                    .get("tela_atual", {})
                    .get("url")
                )
                if event_url and event_url != page.url:
                    try:
                        await page.goto(event_url, timeout=15000, wait_until="domcontentloaded")
                        await asyncio.sleep(0.8)  # aguarda SPA renderizar
                    except Exception as nav_err:
                        _print(f"  [{idx:02d}] aviso: nao navegou para {event_url[:60]} ({nav_err})")

                state = await observer.observe(page)
                intent = interpreter.interpret(obs, state)
                risk = policy.evaluate(intent)
                skills = skill_memory.retrieve(state, intent)
                rctx = ResolutionContext(intent=intent, screen_state=state, known_skills=[s.model_dump() for s in skills])
                try:
                    resolved, trace = await resolver.resolve(page, rctx)
                    ok = True
                except RuntimeError:
                    resolved = None
                    trace = type("T", (), {"steps": ["all_strategies_failed"]})()
                    ok = False
                records.append({
                    "event_id": obs.event_id, "step": idx,
                    "intent": intent.model_dump(), "risk": risk.model_dump(),
                    "resolved": resolved.model_dump() if resolved else None,
                    "resolution_ok": ok, "trace": trace.steps,
                    "skills_matched": len(skills), "screen_fp": state.fingerprint,
                })
                st = "OK" if ok else "XX"
                strat = resolved.strategy_used if resolved else "none"
                _print(f"  [{idx:02d}] {st} {intent.goal_type:10s} | {intent.semantic_target[:35]:35s} | {strat:12s} | conf={intent.semantic_confidence:.2f}")
                await asyncio.sleep(0.3)
            except Exception as exc:
                _print(f"  [{idx:02d}] ERRO: {exc}")
                records.append({"event_id": f"err_{idx}", "error": str(exc)})

        await context.close()
        await browser.close()
    return records


def _summary(records: list[dict]) -> None:
    _sep("=")
    total = len(records)
    ok = sum(1 for r in records if r.get("resolution_ok", False))
    errors = sum(1 for r in records if "error" in r)
    rate = ok / (total - errors) * 100 if (total - errors) > 0 else 0
    print(f"  Total de eventos   : {total}")
    print(f"  Resolvidos         : {ok}")
    print(f"  Falhas de resolucao: {total - ok - errors}")
    print(f"  Erros              : {errors}")
    print(f"  Taxa de resolucao  : {rate:.1f}%")
    strategies: dict[str, int] = {}
    for r in records:
        if r.get("resolved"):
            s = r["resolved"].get("strategy_used", "?")
            strategies[s] = strategies.get(s, 0) + 1
    if strategies:
        print("\n  Strategies usadas:")
        for s, c in sorted(strategies.items(), key=lambda x: -x[1]):
            print(f"    {s:20s}: {c}")
    goals: dict[str, int] = {}
    for r in records:
        if r.get("intent"):
            g = r["intent"].get("goal_type", "?")
            goals[g] = goals.get(g, 0) + 1
    if goals:
        print("\n  Goal types inferidos:")
        for g, c in sorted(goals.items(), key=lambda x: -x[1]):
            print(f"    {g:20s}: {c}")
    _sep("=")


async def main() -> None:
    positional = []
    skip_next = False
    for a in _cli:
        if skip_next:
            skip_next = False
            continue
        if a == "--max-events":
            skip_next = True
            continue
        if not a.startswith("--"):
            positional.append(a)
    if not positional:
        print("Uso: py scripts/run_shadow_homolog.py <shadow.jsonl> [--dry-run] [--headless] [--max-events N]")
        sys.exit(1)

    shadow_path = Path(positional[0])
    if not shadow_path.exists():
        print(f"Arquivo nao encontrado: {shadow_path}")
        sys.exit(1)

    _sep("=")
    _print("Shadow Mode Homologation Runner")
    _print(f"Arquivo  : {shadow_path}")
    _print(f"Modo     : {'DRY-RUN (sem browser)' if DRY_RUN else 'LIVE (com browser)'}")
    _print(f"Headless : {HEADLESS}")
    _sep("=")

    events = _load_events(shadow_path)
    if MAX_EVENTS > 0:
        events = events[:MAX_EVENTS]
        _print(f"Limitado a {MAX_EVENTS} eventos")

    if not events:
        _print("Nenhum evento util encontrado.")
        sys.exit(0)

    from cil.skill_memory import JsonlSkillBackend, SkillMemory
    from orchestration.offline_pipeline import OfflinePipeline
    SKILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    backend = JsonlSkillBackend(SKILLS_PATH)
    # Recria a memoria a cada execucao para evitar acumulo
    skill_memory = SkillMemory()
    pipeline = OfflinePipeline(skill_memory=skill_memory)
    _, report = pipeline.run(shadow_path)
    _print(f"Skills: {report['skills_generated']} geradas, {len(skill_memory._items)} total na memoria")

    _sep()
    _print("Iniciando pipeline semantico...")
    _sep()

    t0 = time.perf_counter()
    records = await _run_dry(events, skill_memory) if DRY_RUN else await _run_live(events, skill_memory)
    elapsed = time.perf_counter() - t0

    from orchestration.evaluation_logger import EvaluationLogger
    logger = EvaluationLogger(root=str(ROOT / "runtime_artifacts" / "homolog_evals"))
    for r in records:
        if "error" not in r:
            logger.append({
                "event_id": r.get("event_id"),
                "intent": r.get("intent"),
                "resolved_target": r.get("resolved") or {},
                "execution_result": {
                    "status": "shadow_only",
                    "effect_verified": r.get("resolution_ok", False),
                    "duration_ms": 0,
                },
                "trace": r.get("trace", []),
            })

    _sep()
    _print(f"Concluido em {elapsed:.1f}s")
    _summary(records)

    out = ROOT / "runtime_artifacts" / "homolog_evals" / f"homolog_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"shadow_file": str(shadow_path), "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    _print(f"Resultados: {out}")

    try:
        metrics = logger.aggregate()
        _print(f"Taxa de resolucao (logger): {metrics['effect_verified_rate']*100:.1f}%")
    except Exception as exc:
        _print(f"Metricas indisponiveis: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
