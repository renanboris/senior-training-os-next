from __future__ import annotations

import pytest
from pydantic import ValidationError

from contracts.intent_action import ExpectedEffect, IntentAction


def _valid() -> IntentAction:
    return IntentAction(
        intent_id="int_001",
        goal_type="search",
        semantic_target="Pesquisar documento",
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="Atualiza grade"),
    )


def test_intent_action_instantiation():
    ia = _valid()
    assert ia.intent_id == "int_001"
    assert ia.goal_type == "search"
    assert ia.semantic_confidence == 0.5


def test_intent_action_invalid_goal_type():
    with pytest.raises(ValidationError):
        IntentAction(
            intent_id="int_001",
            goal_type="invalid_goal",
            semantic_target="Algo",
            expected_effect=ExpectedEffect(effect_type="screen_change", description="x"),
        )


def test_intent_action_confidence_below_zero():
    with pytest.raises(ValidationError):
        IntentAction(
            intent_id="int_001",
            goal_type="search",
            semantic_target="Algo",
            semantic_confidence=-0.1,
            expected_effect=ExpectedEffect(effect_type="screen_change", description="x"),
        )


def test_intent_action_confidence_above_one():
    with pytest.raises(ValidationError):
        IntentAction(
            intent_id="int_001",
            goal_type="search",
            semantic_target="Algo",
            semantic_confidence=1.1,
            expected_effect=ExpectedEffect(effect_type="screen_change", description="x"),
        )


def test_intent_action_json_round_trip():
    ia = _valid()
    # Feature: enterprise-semantic-automation, Property 22: Round-trip de serialização
    restored = IntentAction.model_validate(ia.model_dump())
    assert restored == ia


def test_intent_action_reasoning_trace_default():
    ia = _valid()
    assert ia.reasoning_trace == []
