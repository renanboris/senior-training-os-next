from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from orchestration.evaluation_logger import EvaluationLogger


def _make_record(status: str = "success", verified: bool = True, strategy: str = "dom", duration_ms: int = 100) -> dict:
    return {
        "execution_result": {
            "status": status,
            "effect_verified": verified,
            "duration_ms": duration_ms,
        },
        "resolved_target": {"strategy_used": strategy},
    }


def test_aggregate_nonexistent_file(tmp_path: Path) -> None:
    logger = EvaluationLogger(root=str(tmp_path))
    result = logger.aggregate("2099-01-01")
    assert result["total_executions"] == 0
    assert result["success_rate"] == 0.0
    assert result["strategy_distribution"] == {}


def test_append_creates_newline_separated_records(tmp_path: Path) -> None:
    logger = EvaluationLogger(root=str(tmp_path))
    logger.append(_make_record())
    logger.append(_make_record(status="failed"))

    day = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%d")
    path = tmp_path / f"shadow_eval_{day}.jsonl"
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2


def test_aggregate_counts_correctly(tmp_path: Path) -> None:
    logger = EvaluationLogger(root=str(tmp_path))
    for _ in range(3):
        logger.append(_make_record("success", True, "dom", 50))
    logger.append(_make_record("failed", False, "cache", 200))

    result = logger.aggregate()
    assert result["total_executions"] == 4
    assert result["success_rate"] == 0.75
    assert result["effect_verified_rate"] == 0.75
    assert result["strategy_distribution"]["dom"] == 3
    assert result["strategy_distribution"]["cache"] == 1


def test_export_csv_creates_file(tmp_path: Path) -> None:
    logger = EvaluationLogger(root=str(tmp_path))
    logger.append(_make_record())
    out = tmp_path / "metrics.csv"
    logger.export_csv(None, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "total_executions" in content


# Feature: enterprise-semantic-automation, Property 20: aggregate() conta corretamente N registros
@given(n=st.integers(min_value=1, max_value=20))
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_aggregate_counts_n_records(n: int, tmp_path: Path) -> None:
    import uuid
    # Usa subdiretório único por execução para evitar acúmulo entre exemplos
    unique_root = tmp_path / uuid.uuid4().hex
    logger = EvaluationLogger(root=str(unique_root))
    for _ in range(n):
        logger.append(_make_record())

    result = logger.aggregate()
    assert result["total_executions"] == n

    # Verifica que o arquivo tem exatamente N linhas não-vazias
    import datetime
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    path = unique_root / f"shadow_eval_{day}.jsonl"
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == n
