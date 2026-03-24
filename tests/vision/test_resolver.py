import pytest

from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.screen_state import ScreenState
from vision.resolver import TargetResolver
from vision.strategies.base import ResolutionContext, Strategy
from contracts.resolved_target import ResolvedTarget, ResolvedNode


class FakeStrategy(Strategy):
    name = "fake"

    async def try_resolve(self, page, ctx):
        return ResolvedTarget(
            resolution_id="res_001",
            intent_id=ctx.intent.intent_id,
            strategy_used="dom",
            resolved_target=ResolvedNode(selector="button[aria-label='Pesquisar']"),
            resolution_confidence=0.95,
        )


@pytest.mark.asyncio
async def test_resolver_returns_first_successful_strategy():
    resolver = TargetResolver([FakeStrategy()])
    intent = IntentAction(
        intent_id="int_001",
        goal_type="search",
        semantic_target="Pesquisar",
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="Atualiza grade"),
    )
    ctx = ResolutionContext(intent=intent, screen_state=ScreenState(url="/ged"))

    result, trace = await resolver.resolve(page=None, ctx=ctx)

    assert result.strategy_used == "dom"
    assert any("vencedora" in step for step in trace.steps)