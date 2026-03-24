from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.resolved_target import ResolvedNode, ResolvedTarget
from vision.validator import ResolutionValidator


def test_validator_requires_hard_validation_for_high_risk_action():
    intent = IntentAction(
        intent_id="int_001",
        goal_type="save",
        semantic_target="Salvar",
        expected_effect=ExpectedEffect(effect_type="record_saved", description="Registro salvo"),
    )
    target = ResolvedTarget(
        resolution_id="res_001",
        intent_id="int_001",
        strategy_used="dom",
        resolved_target=ResolvedNode(selector="button[aria-label='Salvar']"),
        resolution_confidence=0.91,
    )

    assert ResolutionValidator().requires_hard_validation(intent, target) is True