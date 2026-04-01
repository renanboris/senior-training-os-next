from __future__ import annotations

import pytest
from pydantic import ValidationError

from contracts.execution_result import ExecutionResult, ExecutionTelemetry


def _valid() -> ExecutionResult:
    return ExecutionResult(
        execution_id="exe_001",
        intent_id="int_001",
        resolution_id="res_001",
        status="success",
    )


def test_execution_result_instantiation():
    r = _valid()
    assert r.execution_id == "exe_001"
    assert r.status == "success"
    assert r.effect_verified is False
    assert r.duration_ms == 0


def test_execution_result_invalid_status():
    with pytest.raises(ValidationError):
        ExecutionResult(
            execution_id="exe_001",
            intent_id="int_001",
            resolution_id="res_001",
            status="unknown_status",
        )


def test_execution_result_json_round_trip():
    r = _valid()
    # Feature: enterprise-semantic-automation, Property 22: Round-trip de serialização
    restored = ExecutionResult.model_validate(r.model_dump())
    assert restored == r


def test_execution_result_json_string_round_trip():
    r = _valid()
    restored = ExecutionResult.model_validate_json(r.model_dump_json())
    assert restored == r


def test_execution_result_telemetry_defaults():
    r = _valid()
    assert r.telemetry == ExecutionTelemetry()
    assert r.telemetry.capture_confidence is None


def test_execution_result_all_statuses():
    for status in ("success", "failed", "partial", "aborted"):
        r = ExecutionResult(
            execution_id="exe_x",
            intent_id="int_x",
            resolution_id="res_x",
            status=status,
        )
        assert r.status == status
