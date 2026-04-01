"""TutorialPlayer — orquestrador principal do Tutorial Player.

Transforma um shadow.jsonl em um tutorial navegado, narrado e gravado.
"""
from __future__ import annotations

import asyncio
import os
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from capture.shadow_ingestion import filter_useful_events, load_jsonl
from cil.interpreter import IntentInterpreter
from cil.observer import ScreenObserver
from cil.skill_memory import SkillMemory
from contracts.observed_action import RelativeBox
from runtime.job_manifest import JobManifest, JobManifestStore, TimelineAudioItem
from runtime.session_bootstrap import AuthenticationError, SessionConfig
from tutorial.highlight import ElementHighlight
from tutorial.humanizer import HumanizedDelay
from tutorial.step_processor import StepProcessor
from vision.resolver import TargetResolver
from vision.strategies.active_element_strategy import ActiveElementStrategy
from vision.strategies.coordinate_strategy import CoordinateStrategy
from vision.strategies.dom_strategy import DomStrategy
from vision.strategies.frame_strategy import FrameStrategy


@dataclass
class TutorialConfig:
    shadow_path: Path
    mode: Literal["replay", "guide", "record-only"] = "replay"
    headless: bool = False
    min_step_duration: float = 1.5
    speed_factor: float = 1.0
    max_events: int = 0
    senior_url: str = os.getenv(
        "SENIOR_URL",
        "https://platform-homologx.senior.com.br/tecnologia/platform/senior-x/#/",
    )


@dataclass
class ArtifactPaths:
    root: Path
    audio_dir: Path
    raw_dir: Path
    output_mp4: Path
    output_srt: Path
    manifest_copy: Path


class TutorialPlayer:
    """Orquestra a reprodução de sessões capturadas como tutoriais humanizados."""

    def __init__(self, config: TutorialConfig, skill_memory: SkillMemory) -> None:
        self.config = config
        self.skill_memory = skill_memory
        self._manifest: Optional[JobManifest] = None
        self._manifest_store: Optional[JobManifestStore] = None

    def _build_artifact_paths(self, job_id: str) -> ArtifactPaths:
        root = Path("runtime_artifacts") / "tutorials" / job_id
        return ArtifactPaths(
            root=root,
            audio_dir=root / "audio",
            raw_dir=root / "raw",
            output_mp4=root / f"{job_id}.mp4",
            output_srt=root / f"{job_id}.srt",
            manifest_copy=root / f"{job_id}_manifest.json",
        )

    async def _setup_session(self, paths: ArtifactPaths):
        from playwright.async_api import async_playwright
        paths.audio_dir.mkdir(parents=True, exist_ok=True)
        paths.raw_dir.mkdir(parents=True, exist_ok=True)

        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=self.config.headless)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(paths.raw_dir),
        )
        page = await context.new_page()
        return pw, browser, context, page

    async def _do_login(self, page) -> None:
        """Login SSO Senior X em 2 etapas com JS direto no DOM."""
        user = os.getenv("SENIOR_USER", "")
        pwd = os.getenv("SENIOR_PASS", "")
        if not user or not pwd:
            raise AuthenticationError("SENIOR_USER e SENIOR_PASS nao configurados.")

        await page.goto(self.config.senior_url)
        await page.wait_for_load_state("domcontentloaded", timeout=30000)

        # Etapa 1: preenche email
        for sel in ["input#username-input-field", "input[type='email']"]:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.fill(user)
                    break
            except Exception:
                continue

        # Clica nextBtn
        await page.locator("button#nextBtn").click(force=True)
        await asyncio.sleep(2.0)

        # Etapa 2: preenche senha via JS
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

        # Clica loginbtn via JS
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

        # Aguarda redirect
        try:
            await page.wait_for_url(
                lambda url: "login" not in url and "sso" not in url and "openid-connect" not in url,
                timeout=45000,
            )
        except Exception:
            pass
        await page.wait_for_load_state("networkidle", timeout=30000)

    async def _teardown_session(self, context, paths: ArtifactPaths) -> str:
        """Fecha o contexto e aguarda o vídeo bruto ser salvo."""
        await context.close()

        # Aguarda o arquivo de vídeo aparecer (timeout 10s)
        for _ in range(20):
            videos = list(paths.raw_dir.glob("*.webm")) + list(paths.raw_dir.glob("*.mp4"))
            if videos:
                return str(videos[0])
            await asyncio.sleep(0.5)

        raise FileNotFoundError(f"Video bruto nao encontrado em {paths.raw_dir}")

    async def _render_final_video(self, manifest: JobManifest, paths: ArtifactPaths) -> None:
        """Renderiza o vídeo final com áudio TTS e legendas."""
        from runtime.media_pipeline import VideoRenderer
        timeline = [
            {
                "step_id": item.step_id,
                "text": item.text,
                "audio_file": item.audio_file,
                "start_sec": item.start_sec,
                "end_sec": item.end_sec,
            }
            for item in manifest.audio_timeline
        ]
        try:
            VideoRenderer().render(
                browser_video_path=manifest.browser_video_path,
                timeline=timeline,
                output_mp4_path=str(paths.output_mp4),
                output_srt_path=str(paths.output_srt),
                cut_start_sec=manifest.cut_start_sec,
                logger=None,
            )
            print(f"Video: {paths.output_mp4.resolve()}")
            print(f"Legendas: {paths.output_srt.resolve()}")
        except Exception as exc:
            print(f"ERRO na renderizacao: {exc}", file=sys.stderr)
            if self._manifest_store and self._manifest:
                self._manifest_store.save(self._manifest)
            sys.exit(1)

    async def run(self) -> JobManifest:
        """Executa o Tutorial Player completo."""
        cfg = self.config

        # 1. Carrega e valida eventos
        if not cfg.shadow_path.exists():
            print(f"Arquivo nao encontrado: {cfg.shadow_path}", file=sys.stderr)
            sys.exit(1)

        events = load_jsonl(cfg.shadow_path)
        useful = filter_useful_events(events)
        if not useful:
            print("Nenhum evento util encontrado.", file=sys.stderr)
            sys.exit(1)

        if cfg.max_events > 0:
            useful = useful[:cfg.max_events]

        print(f"Eventos: {len(events)} totais -> {len(useful)} uteis")

        # 2. Cria JobManifest e diretórios
        job_id = uuid4().hex[:16]
        paths = self._build_artifact_paths(job_id)
        manifest = JobManifest(
            job_id=job_id,
            training_id=job_id,
            lesson_name=cfg.shadow_path.stem,
            created_at=datetime.now(timezone.utc),
        )
        self._manifest = manifest
        manifest_store = JobManifestStore(root="runtime_artifacts/jobs")
        self._manifest_store = manifest_store

        # 3. Handler SIGINT/SIGTERM
        def _handle_signal(sig, frame):
            print("\nInterrompido. Salvando manifest parcial...")
            manifest_store.save(manifest)
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_signal)
        try:
            signal.signal(signal.SIGTERM, _handle_signal)
        except (OSError, ValueError):
            pass

        # 4. Inicializa componentes
        from runtime.media_pipeline import TTSService, VideoRenderer
        tts = TTSService()
        humanizer = HumanizedDelay(
            min_step_duration=cfg.min_step_duration,
            speed_factor=cfg.speed_factor,
        )

        # Lookup de coordenadas do shadow para CoordinateStrategy
        coord_lookup: dict[str, dict] = {}
        for ev in useful:
            el = ev.get("elemento_alvo") or {}
            t = (ev.get("business_target") or el.get("label_curto") or "").strip()
            c = el.get("coordenadas_relativas")
            if t and c:
                coord_lookup[t.lower()] = c

        resolver = TargetResolver(strategies=[
            ActiveElementStrategy(),
            DomStrategy(),
            FrameStrategy(),
            CoordinateStrategy(coordinate_lookup=lambda t: coord_lookup.get(t.lower())),
        ])

        # Adapters para ActionExecutor
        async def tutorial_click_adapter(page, target):
            if isinstance(target, str):
                await page.locator(target).first.click()
            elif isinstance(target, RelativeBox):
                x = int(target.x_pct * 1440)
                y = int(target.y_pct * 900)
                await page.mouse.click(x, y)

        async def tutorial_type_adapter(page, text):
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

        from runtime.executor import ActionExecutor
        executor = ActionExecutor(
            click_adapter=tutorial_click_adapter,
            type_adapter=tutorial_type_adapter,
        )

        step_proc = StepProcessor(
            mode=cfg.mode,
            resolver=resolver,
            executor=executor if cfg.mode == "replay" else None,
            highlight=ElementHighlight(),
            observer=ScreenObserver(),
            interpreter=IntentInterpreter(),
            skill_memory=self.skill_memory,
            humanizer=humanizer,
        )

        # 5. Inicia sessão Playwright
        pw, browser, context, page = await self._setup_session(paths)

        # 6. Login (não em record-only)
        if cfg.mode != "record-only":
            print("Fazendo login no Senior X...")
            await self._do_login(page)
            print(f"Login OK -> {page.url[:80]}")

        # 7. Loop de Steps
        print(f"Processando {len(useful)} eventos em modo {cfg.mode}...")
        cursor_sec = 0.0
        total = len(useful)

        for idx, event in enumerate(useful, 1):
            narration = event.get("micro_narracao") or event.get("intencao_semantica") or ""

            # Gera áudio TTS
            audio_file = None
            audio_duration = 0.0
            if narration.strip():
                audio_out = str(paths.audio_dir / f"step_{idx:03d}.mp3")
                try:
                    audio_file = await tts.generate_audio(narration, audio_out)
                    if audio_file:
                        try:
                            from moviepy import AudioFileClip
                        except ImportError:
                            from moviepy.editor import AudioFileClip
                        clip = AudioFileClip(audio_file)
                        audio_duration = clip.duration
                        clip.close()
                except Exception:
                    audio_file = None
                    audio_duration = 0.0

            # Acumula timeline
            if audio_file:
                manifest.audio_timeline.append(TimelineAudioItem(
                    step_id=f"step_{idx:03d}",
                    text=narration,
                    audio_file=audio_file,
                    start_sec=cursor_sec,
                    end_sec=cursor_sec + audio_duration,
                ))
                cursor_sec += audio_duration

            # Processa o step
            result = await step_proc.process(
                page=page,
                event=event,
                step_index=idx,
                total_steps=total,
                lesson_name=cfg.shadow_path.stem,
                audio_file=audio_file,
                audio_duration=audio_duration,
            )

            status_icon = "OK" if result.status == "success" else "!!"
            print(
                f"  [{idx:02d}] {status_icon} {result.status:20s} | "
                f"{event.get('business_target', '')[:35]:35s} | "
                f"strategy={result.strategy_used or 'none'}"
            )

            # Salva manifest incremental
            manifest_store.save(manifest)

        # 8. Teardown e renderização
        try:
            video_path = await self._teardown_session(context, paths)
            await browser.close()
            await pw.stop()
            manifest.browser_video_path = video_path
        except FileNotFoundError as exc:
            print(f"ERRO: {exc}", file=sys.stderr)
            await browser.close()
            await pw.stop()
            sys.exit(1)

        manifest.output_mp4_path = str(paths.output_mp4)
        manifest.output_srt_path = str(paths.output_srt)

        await self._render_final_video(manifest, paths)

        # Save final
        manifest_store.save(manifest)
        import shutil
        shutil.copy(
            manifest_store.root / f"{job_id}.json",
            paths.manifest_copy,
        )

        return manifest
