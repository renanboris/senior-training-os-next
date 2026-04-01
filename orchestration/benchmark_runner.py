"""BenchmarkRunner — executa suítes de benchmark automatizadas.

CLI:
    python -m orchestration.benchmark_runner <suite.json>
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from cil.text_utils import SimilarityMatcher


class BenchmarkCase(TypedDict):
    objective: str
    shadow_jsonl_path: str
    expected_skills: list[dict]  # [{semantic_target, goal_type}]


class CaseResult(TypedDict):
    case_objective: str
    precision: float
    recall: float
    f1_score: float
    passed: bool


class BenchmarkReport(TypedDict):
    timestamp: str
    total_cases: int
    passed: int
    failed: int
    precision: float
    recall: float
    f1_score: float
    cases: list[CaseResult]


class BenchmarkRunner:
    def __init__(self, offline_pipeline, matcher: SimilarityMatcher | None = None) -> None:
        self._pipeline = offline_pipeline
        self._matcher = matcher or SimilarityMatcher()

    def run(self, cases: list[BenchmarkCase]) -> BenchmarkReport:
        case_results: list[CaseResult] = []

        for case in cases:
            result = self._run_case(case)
            case_results.append(result)

        total = len(case_results)
        passed = sum(1 for r in case_results if r["passed"])
        failed = total - passed

        agg_precision = sum(r["precision"] for r in case_results) / total if total else 0.0
        agg_recall = sum(r["recall"] for r in case_results) / total if total else 0.0
        agg_f1 = self._f1(agg_precision, agg_recall)

        report: BenchmarkReport = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_cases": total,
            "passed": passed,
            "failed": failed,
            "precision": round(agg_precision, 4),
            "recall": round(agg_recall, 4),
            "f1_score": round(agg_f1, 4),
            "cases": case_results,
        }

        self._persist(report)
        return report

    def _run_case(self, case: BenchmarkCase) -> CaseResult:
        path = Path(case["shadow_jsonl_path"])
        expected = case.get("expected_skills", [])

        try:
            skills, _ = self._pipeline.run(path)
        except Exception:
            skills = []

        precision, recall = self._compute_metrics(skills, expected)
        f1 = self._f1(precision, recall)

        return CaseResult(
            case_objective=case["objective"],
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            passed=f1 >= 0.8,
        )

    def _compute_metrics(self, generated, expected: list[dict]) -> tuple[float, float]:
        if not generated and not expected:
            return 1.0, 1.0
        if not generated:
            return 0.0, 0.0
        if not expected:
            return 0.0, 0.0

        threshold = 0.8
        true_positives = 0

        for exp in expected:
            exp_target = exp.get("semantic_target", "")
            exp_goal = exp.get("goal_type", "")
            for gen in generated:
                if gen.goal_type != exp_goal:
                    continue
                score = self._matcher.score(gen.semantic_target, exp_target)
                if score >= threshold:
                    true_positives += 1
                    break

        precision = true_positives / len(generated)
        recall = true_positives / len(expected)
        return precision, recall

    @staticmethod
    def _f1(precision: float, recall: float) -> float:
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def _persist(self, report: BenchmarkReport) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = Path("runtime_artifacts") / "benchmarks" / f"{ts}_benchmark.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m orchestration.benchmark_runner <suite.json>", file=sys.stderr)
        sys.exit(1)

    suite_path = Path(sys.argv[1])
    if not suite_path.exists():
        print(f"Arquivo não encontrado: {suite_path}", file=sys.stderr)
        sys.exit(1)

    cases: list[BenchmarkCase] = json.loads(suite_path.read_text(encoding="utf-8"))

    from cil.skill_memory import SkillMemory
    from orchestration.offline_pipeline import OfflinePipeline

    pipeline = OfflinePipeline(skill_memory=SkillMemory())
    runner = BenchmarkRunner(offline_pipeline=pipeline)
    report = runner.run(cases)

    print(json.dumps(report, ensure_ascii=False, indent=2))

    any_failed = any(not r["passed"] for r in report["cases"])
    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    _main()
