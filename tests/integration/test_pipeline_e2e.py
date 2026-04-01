"""Testes de integração end-to-end do pipeline semântico.

Exercita o fluxo completo sem browser real usando mocks de page.
Deve completar em < 5s.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.known_skill import KnownSkill
from contracts.observed_action import ObservedAction, RawTarget, ScreenSnapshot, StateChange
from contracts.screen_state import ScreenState
from cil.interpreter import IntentInterpreter
from cil.skill_memory import SkillMemory
from runtime.effect_verifier import EffectVerifier
from vision.resolver import TargetResolver
from vision.strategies.base import ResolutionContext
from vision.strategies.dom_strategy import DomStrategy


def _make_page_mock(count: int = 1):
    locator = AsyncMock()
    locator.count = AsyncMock(return_value=count)
    page = MagicMock()
    page.get_by_role = MagicMock(return_value=locator)
    page.get_by_label = MagicMock(return_value=locator)
    page.get_by_placeholder = MagicMock(return_value=locator)
    return page


@pytest.mark.asyncio
async def test_full_pipeline_observed_action_to_effect_verified():
    """Fluxo: ObservedAction → IntentInterpreter → SkillMemory.retrieve → DomStrategy → EffectVerifier."""
    # 1. ObservedAction
    observed = ObservedAction(
        event_id="obs_e2e_001",
        timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        action_type="type_and_enter",
        raw_target=RawTarget(text="Pesquisar"),
        typed_value="documento fiscal",
        screen_before=ScreenSnapshot(url="/ged", title="GED"),
        state_change=StateChange(changed=True, change_type="grid_refresh"),
        capture_confidence=0.92,
    )
    state = ScreenState(url="/ged", title="GED", primary_area="ged", fingerprint="ged::ged::modal=0::ged::")

    # 2. IntentInterpreter
    interpreter = IntentInterpreter()
    intent = interpreter.interpret(observed, state)
    assert intent.goal_type == "search"
    assert intent.semantic_target == "Pesquisar"

    # 3. SkillMemory.retrieve
    memory = SkillMemory()
    memory.seed([
        KnownSkill(
            skill_id="skill_e2e",
            semantic_target="Pesquisar",
            goal_type="search",
            screen_fingerprint="ged::ged::modal=0::ged::",
            confidence=0.9,
        )
    ])
    matches = memory.retrieve(state, intent)
    assert len(matches) >= 1

    # 4. DomStrategy com mock de page
    page = _make_page_mock(count=1)
    ctx = ResolutionContext(intent=intent, screen_state=state)
    resolver = TargetResolver(strategies=[DomStrategy()])
    resolved, trace = await resolver.resolve(page, ctx)
    assert resolved is not None
    assert not resolved.resolved_target.selector.startswith("semantic:")

    # 5. EffectVerifier
    before = ScreenSnapshot(url="/ged", title="GED", grid_row_count=5)
    after = ScreenSnapshot(url="/ged", title="GED", grid_row_count=10)
    verifier = EffectVerifier()
    ok, msg = verifier.verify(intent, before, after)
    assert ok is True


@pytest.mark.asyncio
async def test_pipeline_with_skill_memory_and_planner():
    """Fluxo: SkillMemory seed → Planner → IntentAction válida."""
    from cil.planner import Planner

    state = ScreenState(url="/ged", primary_area="ged")
    skills = [
        KnownSkill(skill_id="s1", semantic_target="Pesquisar documento", goal_type="search", confidence=0.9),
    ]
    memory = SkillMemory()
    memory.seed(skills)

    planner = Planner()
    intent = planner.next_action("Pesquisar documento no GED", state, [], skills)
    assert intent.goal_type == "search"
    assert intent.semantic_target is not None
