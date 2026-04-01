from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import AsyncMock, MagicMock

from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.screen_state import ScreenState
from vision.strategies.base import ResolutionContext
from vision.strategies.dom_strategy import DomStrategy


def _make_page_mock(count: int = 1):
    """Cria mock de page que retorna count para qualquer locator."""
    locator_mock = AsyncMock()
    locator_mock.count = AsyncMock(return_value=count)
    page = MagicMock()
    page.get_by_role = MagicMock(return_value=locator_mock)
    page.get_by_label = MagicMock(return_value=locator_mock)
    page.get_by_placeholder = MagicMock(return_value=locator_mock)
    return page


def _make_ctx(target: str) -> ResolutionContext:
    intent = IntentAction(
        intent_id="int_001",
        goal_type="search",
        semantic_target=target,
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="x"),
    )
    return ResolutionContext(intent=intent, screen_state=ScreenState(url="/ged"))


@pytest.mark.asyncio
async def test_dom_strategy_returns_role_selector():
    page = _make_page_mock(count=1)
    ctx = _make_ctx("Pesquisar")
    result = await DomStrategy().try_resolve(page, ctx)
    assert result is not None
    assert result.resolved_target.selector == 'role=button[name="Pesquisar"]'


@pytest.mark.asyncio
async def test_dom_strategy_returns_none_when_not_found():
    page = _make_page_mock(count=0)
    ctx = _make_ctx("Inexistente")
    result = await DomStrategy().try_resolve(page, ctx)
    assert result is None


@pytest.mark.asyncio
async def test_dom_strategy_empty_target_returns_none():
    page = _make_page_mock(count=1)
    ctx = _make_ctx("")
    result = await DomStrategy().try_resolve(page, ctx)
    assert result is None


# Feature: enterprise-semantic-automation, Property 1: DomStrategy nunca produz selector com prefixo semantic:
@given(target_text=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()))
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_dom_strategy_selector_never_semantic_prefix(target_text: str):
    page = _make_page_mock(count=1)
    ctx = _make_ctx(target_text.strip())
    result = await DomStrategy().try_resolve(page, ctx)
    if result is not None and result.resolved_target.selector:
        assert not result.resolved_target.selector.startswith("semantic:")
