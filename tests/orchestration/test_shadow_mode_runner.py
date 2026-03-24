import pytest
from datetime import datetime, timezone

from orchestration.shadow_mode_runner import ShadowModeRunner
from orchestration.legacy_bridge import LegacyBridge
from contracts.observed_action import ObservedAction, RawTarget, ScreenSnapshot
from contracts.execution_result import ExecutionResult
from contracts.resolved_target import ResolvedTarget, ResolvedNode


class FakeResolver:
    async def resolve(self, page, ctx):
        return (
            ResolvedTarget(
                resolution_id="res_001",
                intent_id=ctx.intent.intent_id,
                strategy_used="dom",
                resolved_target=ResolvedNode(selector="button[aria-label='Pesquisar']"),
                resolution_confidence=0.93,
            ),
            type("Trace", (), {"steps": ["fake trace"]})(),
        )


class FakeExecutor:
    async def execute(self, **kwargs):
        return ExecutionResult(
            execution_id="exe_001",
            intent_id=kwargs["intent"].intent_id,
            resolution_id=kwargs["target"].resolution_id,
            status="success",
        )


class FakeSkillMemory:
    def retrieve(self, state, intent):
        return []


class FakePage:
    url = "/ged"
    frames = []

    async def title(self):
        return "GED"

    async def evaluate(self, script):
        if "querySelectorAll" in script:
            return [
                {"kind": "input", "label": "Pesquisar", "role": None},
                {"kind": "button", "label": "Buscar", "role": "button"},
            ]
        if "document.activeElement" in script:
            return None
        if "document.body" in script:
            return "GED documentos pesquisar"
        if "querySelector(" in script:
            return False
        return None


@pytest.mark.asyncio
async def test_shadow_mode_runner_generates_record(tmp_path):
    page = FakePage()
    observed = ObservedAction(
        event_id="obs_001",
        timestamp=datetime.now(timezone.utc),
        action_type="click",
        raw_target=RawTarget(text="Pesquisar"),
        screen_before=ScreenSnapshot(url="/ged", title="GED"),
        capture_confidence=0.88,
    )

    from orchestration.evaluation_logger import EvaluationLogger
    logger = EvaluationLogger(root=str(tmp_path))

    runner = ShadowModeRunner(
        resolver=FakeResolver(),
        executor=FakeExecutor(),
        skill_memory=FakeSkillMemory(),
        legacy_bridge=LegacyBridge(),
        logger=logger,
    )

    result = await runner.run_from_observed_action(
        page=page,
        observed_action=observed,
        lesson_name="GED teste",
        step_index=1,
        total_steps=5,
    )

    assert "record" in result
    assert result["record"]["intent"]["goal_type"] in {"search", "navigate"}