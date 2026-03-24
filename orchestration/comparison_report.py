from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComparisonResult:
    same_goal_type: bool
    same_semantic_target: bool
    execution_success: bool
    resolution_strategy: str | None
    notes: list[str]


class ComparisonReportBuilder:
    def compare(self, legacy_step: dict | None, inferred_intent, execution_result, resolved_target) -> ComparisonResult:
        notes: list[str] = []

        legacy_goal = None
        legacy_target = None
        if legacy_step:
            legacy_goal = legacy_step.get("goal_type") or legacy_step.get("acao_tec", {}).get("tipo")
            legacy_target = legacy_step.get("semantic_target") or legacy_step.get("alvo", {}).get("descricao")

        same_goal = bool(legacy_goal and inferred_intent.goal_type == legacy_goal)
        same_target = bool(
            legacy_target and inferred_intent.semantic_target.lower() == str(legacy_target).lower()
        )

        if not same_goal:
            notes.append("Goal type divergiu entre legado e CIL.")
        if not same_target:
            notes.append("Semantic target divergiu entre legado e CIL.")
        if execution_result.status != "success":
            notes.append("Execução não confirmou sucesso total.")

        return ComparisonResult(
            same_goal_type=same_goal,
            same_semantic_target=same_target,
            execution_success=execution_result.status == "success",
            resolution_strategy=resolved_target.strategy_used if resolved_target else None,
            notes=notes,
        )