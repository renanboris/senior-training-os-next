from orchestration.comparison_report import ComparisonReportBuilder
from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.execution_result import ExecutionResult
from contracts.resolved_target import ResolvedNode, ResolvedTarget


def test_comparison_report_detects_goal_match_and_target_divergence():
    legacy_step = {
        "goal_type": "search",
        "semantic_target": "Buscar documento",
    }
    inferred_intent = IntentAction(
        intent_id="int_001",
        goal_type="search",
        semantic_target="Pesquisar documento",
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="Atualiza grade"),
    )
    execution_result = ExecutionResult(
        execution_id="exe_001",
        intent_id="int_001",
        resolution_id="res_001",
        status="success",
    )
    resolved_target = ResolvedTarget(
        resolution_id="res_001",
        intent_id="int_001",
        strategy_used="dom",
        resolved_target=ResolvedNode(selector="input[name='pesquisa']"),
        resolution_confidence=0.9,
    )

    result = ComparisonReportBuilder().compare(
        legacy_step=legacy_step,
        inferred_intent=inferred_intent,
        execution_result=execution_result,
        resolved_target=resolved_target,
    )

    assert result.same_goal_type is True
    assert result.same_semantic_target is False
    assert result.execution_success is True