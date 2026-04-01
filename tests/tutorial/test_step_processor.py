from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cil.interpreter import IntentInterpreter
from cil.observer import ScreenObserver
from cil.skill_memory import SkillMemory
from tutorial.highlight import ElementHighlight
from tutorial.humanizer import HumanizedDelay
from tutorial.step_processor import StepProcessor

from tests.tutorial.conftest import (
    make_fake_executor,
    make_fake_resolver,
    make_failing_resolver,
)


def _make_processor(mode: str = "replay", resolver=None, executor=None):
    return StepProcessor(
        mode=mode,
        resolver=resolver or make_fake_resolver(),
        executor=executor or make_fake_executor(),
        highlight=ElementHighlight(),
        observer=ScreenObserver(),
        interpreter=IntentInterpreter(),
        skill_memory=SkillMemory(),
        humanizer=HumanizedDelay(min_step_duration=0.01, speed_factor=0.01),
    )


# ---------------------------------------------------------------------------
# Property 10: Navegação condicional
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_navigation_called_on_url_change(mock_page, sample_shadow_event):
    mock_page.url = "https://other.url/"
    processor = _make_processor()
    with patch("tutorial.step_processor.safe_evaluate", new_callable=AsyncMock):
        with patch("tutorial.step_processor.show_subtitle", new_callable=AsyncMock):
            with patch("tutorial.step_processor.remove_subtitle", new_callable=AsyncMock):
                with patch("tutorial.step_processor.update_progress_pill", new_callable=AsyncMock):
                    await processor.process(mock_page, sample_shadow_event, 1, 5, "test")
    mock_page.goto.assert_called_once()


@pytest.mark.asyncio
async def test_navigation_skipped_on_same_url(mock_page, sample_shadow_event):
    # Seta a URL do mock igual à URL do evento
    event_url = sample_shadow_event["contexto_semantico"]["tela_atual"]["url"]
    mock_page.url = event_url
    processor = _make_processor()
    with patch("tutorial.step_processor.safe_evaluate", new_callable=AsyncMock):
        with patch("tutorial.step_processor.show_subtitle", new_callable=AsyncMock):
            with patch("tutorial.step_processor.remove_subtitle", new_callable=AsyncMock):
                with patch("tutorial.step_processor.update_progress_pill", new_callable=AsyncMock):
                    await processor.process(mock_page, sample_shadow_event, 1, 5, "test")
    mock_page.goto.assert_not_called()


# ---------------------------------------------------------------------------
# Property 8: Status válido
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolution_failure_returns_failed_status(mock_page, sample_shadow_event):
    processor = _make_processor(resolver=make_failing_resolver())
    result = await processor.process(mock_page, sample_shadow_event, 1, 5, "test")
    assert result.status == "resolution_failed"


@pytest.mark.asyncio
async def test_execution_partial_returns_partial_status(mock_page, sample_shadow_event):
    processor = _make_processor(executor=make_fake_executor(status="partial"))
    with patch("tutorial.step_processor.safe_evaluate", new_callable=AsyncMock):
        with patch("tutorial.step_processor.show_subtitle", new_callable=AsyncMock):
            with patch("tutorial.step_processor.remove_subtitle", new_callable=AsyncMock):
                with patch("tutorial.step_processor.update_progress_pill", new_callable=AsyncMock):
                    result = await processor.process(mock_page, sample_shadow_event, 1, 5, "test")
    assert result.status == "execution_partial"


# ---------------------------------------------------------------------------
# Property 5: Overlays apenas em replay/guide
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_only_no_overlays(mock_page, sample_shadow_event):
    processor = _make_processor(mode="record-only")
    with patch("tutorial.step_processor.safe_evaluate", new_callable=AsyncMock) as mock_safe:
        with patch("tutorial.step_processor.show_subtitle", new_callable=AsyncMock) as mock_sub:
            with patch("tutorial.step_processor.remove_subtitle", new_callable=AsyncMock):
                with patch("tutorial.step_processor.update_progress_pill", new_callable=AsyncMock):
                    await processor.process(mock_page, sample_shadow_event, 1, 5, "test")
    mock_sub.assert_not_called()
    mock_safe.assert_not_called()


# ---------------------------------------------------------------------------
# Property 4: ActionExecutor apenas em replay
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_guide_no_executor(mock_page, sample_shadow_event):
    executor = make_fake_executor()
    processor = _make_processor(mode="guide", executor=executor)
    with patch("tutorial.step_processor.safe_evaluate", new_callable=AsyncMock):
        with patch("tutorial.step_processor.show_subtitle", new_callable=AsyncMock):
            with patch("tutorial.step_processor.remove_subtitle", new_callable=AsyncMock):
                with patch("tutorial.step_processor.update_progress_pill", new_callable=AsyncMock):
                    await processor.process(mock_page, sample_shadow_event, 1, 5, "test")
    executor.execute.assert_not_called()


@pytest.mark.asyncio
async def test_replay_calls_executor(mock_page, sample_shadow_event):
    executor = make_fake_executor()
    processor = _make_processor(mode="replay", executor=executor)
    with patch("tutorial.step_processor.safe_evaluate", new_callable=AsyncMock):
        with patch("tutorial.step_processor.show_subtitle", new_callable=AsyncMock):
            with patch("tutorial.step_processor.remove_subtitle", new_callable=AsyncMock):
                with patch("tutorial.step_processor.update_progress_pill", new_callable=AsyncMock):
                    await processor.process(mock_page, sample_shadow_event, 1, 5, "test")
    executor.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Property 12: iframe_hint propagado ao ResolutionContext
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_iframe_hint_in_resolution_context(mock_page, sample_shadow_event):
    sample_shadow_event["elemento_alvo"]["iframe_hint"] = "frame[0]"
    captured_ctx = {}

    async def capture_resolve(page, ctx):
        captured_ctx["ctx"] = ctx
        from contracts.resolved_target import ResolvedNode, ResolvedTarget
        resolved = ResolvedTarget(
            resolution_id="res_x", intent_id="int_x",
            strategy_used="coordinates",
            resolved_target=ResolvedNode(),
            resolution_confidence=0.8,
        )
        return resolved, type("T", (), {"steps": []})()

    resolver = MagicMock()
    resolver.resolve = capture_resolve
    processor = _make_processor(resolver=resolver)

    with patch("tutorial.step_processor.safe_evaluate", new_callable=AsyncMock):
        with patch("tutorial.step_processor.show_subtitle", new_callable=AsyncMock):
            with patch("tutorial.step_processor.remove_subtitle", new_callable=AsyncMock):
                with patch("tutorial.step_processor.update_progress_pill", new_callable=AsyncMock):
                    await processor.process(mock_page, sample_shadow_event, 1, 5, "test")

    # Verifica que o iframe_hint foi propagado via known_skills
    ctx = captured_ctx.get("ctx")
    assert ctx is not None
    iframe_hints = [s.get("_iframe_hint") for s in ctx.known_skills if isinstance(s, dict)]
    assert "frame[0]" in iframe_hints
