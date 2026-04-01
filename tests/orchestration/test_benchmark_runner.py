from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from contracts.known_skill import KnownSkill
from orchestration.benchmark_runner import BenchmarkCase, BenchmarkRunner


def _make_pipeline_mock(skills: list[KnownSkill]):
    mock = MagicMock()
    mock.run.return_value = (skills, {"total_events": 1, "useful_events": 1, "skills_generated": len(skills), "skills_discarded": 0})
    return mock


def _skill(target: str, goal: str = "search") -> KnownSkill:
    return KnownSkill(skill_id=f"s_{target[:8]}", semantic_target=target, goal_type=goal, confidence=0.9)


def test_benchmark_empty_cases():
    runner = BenchmarkRunner(offline_pipeline=_make_pipeline_mock([]))
    report = runner.run([])
    assert report["total_cases"] == 0
    assert report["passed"] == 0
    assert report["failed"] == 0
    assert "timestamp" in report
    assert "cases" in report


def test_benchmark_perfect_match(tmp_path: Path):
    skills = [_skill("Pesquisar documento")]
    pipeline = _make_pipeline_mock(skills)
    runner = BenchmarkRunner(offline_pipeline=pipeline)

    cases: list[BenchmarkCase] = [
        {
            "objective": "Pesquisar",
            "shadow_jsonl_path": str(tmp_path / "dummy.jsonl"),
            "expected_skills": [{"semantic_target": "Pesquisar documento", "goal_type": "search"}],
        }
    ]
    report = runner.run(cases)
    assert report["cases"][0]["f1_score"] == 1.0
    assert report["cases"][0]["passed"] is True


def test_benchmark_no_match(tmp_path: Path):
    skills = [_skill("Salvar registro", "save")]
    pipeline = _make_pipeline_mock(skills)
    runner = BenchmarkRunner(offline_pipeline=pipeline)

    cases: list[BenchmarkCase] = [
        {
            "objective": "Pesquisar",
            "shadow_jsonl_path": str(tmp_path / "dummy.jsonl"),
            "expected_skills": [{"semantic_target": "Pesquisar documento", "goal_type": "search"}],
        }
    ]
    report = runner.run(cases)
    assert report["cases"][0]["f1_score"] == 0.0
    assert report["cases"][0]["passed"] is False


# Feature: enterprise-semantic-automation, Property 21: BenchmarkReport contém todos os campos obrigatórios
@given(n=st.integers(min_value=0, max_value=5))
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_benchmark_report_has_required_fields(n: int, tmp_path: Path) -> None:
    import uuid
    pipeline = _make_pipeline_mock([])
    runner = BenchmarkRunner(offline_pipeline=pipeline)
    unique_dir = tmp_path / uuid.uuid4().hex
    cases = [
        BenchmarkCase(
            objective=f"obj_{i}",
            shadow_jsonl_path=str(unique_dir / "dummy.jsonl"),
            expected_skills=[],
        )
        for i in range(n)
    ]
    report = runner.run(cases)
    for field in ("timestamp", "total_cases", "passed", "failed", "precision", "recall", "f1_score", "cases"):
        assert field in report
