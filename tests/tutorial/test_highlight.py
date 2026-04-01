from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import AsyncMock, MagicMock, patch

from contracts.observed_action import RelativeBox
from tutorial.highlight import ElementHighlight


# Feature: tutorial-player, Property 11: Element_Highlight CSS contem valores corretos
@given(
    x=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    y=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    w=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    h=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@settings(max_examples=100)
def test_highlight_css_values(x: float, y: float, w: float, h: float) -> None:
    script = ElementHighlight()._build_inject_script(x, y, w, h)
    assert "#FF6B35" in script
    assert "border-radius" in script
    assert "4px" in script
    assert "rgba(255,107,53,0.3)" in script
    assert "2147483644" in script


@pytest.mark.asyncio
async def test_inject_calls_evaluate_with_coords():
    highlight = ElementHighlight()
    page_mock = MagicMock()
    page_mock.evaluate = AsyncMock(return_value=None)

    coords = RelativeBox(x_pct=0.1, y_pct=0.2, w_pct=0.05, h_pct=0.05)
    await highlight.inject(page_mock, coords_rel=coords)

    page_mock.evaluate.assert_called_once()
    script_arg = page_mock.evaluate.call_args[0][0]
    assert "#FF6B35" in script_arg


@pytest.mark.asyncio
async def test_remove_calls_evaluate():
    highlight = ElementHighlight()
    page_mock = MagicMock()
    page_mock.evaluate = AsyncMock(return_value=None)

    await highlight.remove(page_mock)

    page_mock.evaluate.assert_called_once()
    script_arg = page_mock.evaluate.call_args[0][0]
    assert "senior-element-highlight" in script_arg
    assert "remove()" in script_arg


@pytest.mark.asyncio
async def test_inject_with_none_coords_and_no_selector_does_not_raise():
    highlight = ElementHighlight()
    page_mock = MagicMock()

    with patch("tutorial.highlight.safe_evaluate", new_callable=AsyncMock):
        # Não deve lançar exceção
        await highlight.inject(page_mock, coords_rel=None, selector=None)
