from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from cil.skill_memory import SkillMemory
from orchestration.offline_pipeline import OfflinePipeline, PipelineInputError


def _make_event(target: str = "Pesquisar", noise: bool = False) -> dict:
    return {
        "semantic_action": "navigate",
        "business_target": target,
        "is_noise": noise,
        "capture_scope": "module_iframe",
        "elemento_alvo": {"confianca_captura": "alta"},
        "technical": {},
    }


def _write_jsonl(path: Path, events: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def test_pipeline_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "empty.jsonl"
    f.write_text("", encoding="utf-8")
    memory = SkillMemory()
    pipeline = OfflinePipeline(skill_memory=memory)
    skills, report = pipeline.run(f)
    assert skills == []
    assert report["total_events"] == 0
    assert report["skills_generated"] == 0


def test_pipeline_nonexistent_file(tmp_path: Path) -> None:
    memory = SkillMemory()
    pipeline = OfflinePipeline(skill_memory=memory)
    with pytest.raises(PipelineInputError):
        pipeline.run(tmp_path / "nope.jsonl")


def test_pipeline_filters_noise(tmp_path: Path) -> None:
    f = tmp_path / "data.jsonl"
    events = [_make_event("Pesquisar"), _make_event("Ruído", noise=True), _make_event("Salvar")]
    _write_jsonl(f, events)
    memory = SkillMemory()
    pipeline = OfflinePipeline(skill_memory=memory)
    skills, report = pipeline.run(f)
    assert report["total_events"] == 3
    assert report["useful_events"] == 2
    assert report["skills_generated"] == 2


def test_pipeline_discards_low_confidence(tmp_path: Path) -> None:
    f = tmp_path / "data.jsonl"
    event = {
        "semantic_action": "navigate",
        "business_target": "Alvo",
        "is_noise": False,
        "capture_scope": "module_iframe",
        "elemento_alvo": {"confianca_captura": "baixa"},  # 0.45 < 0.5
        "technical": {},
    }
    _write_jsonl(f, [event])
    memory = SkillMemory()
    pipeline = OfflinePipeline(skill_memory=memory, min_confidence=0.5)
    skills, report = pipeline.run(f)
    assert report["skills_generated"] == 0
    assert report["skills_discarded"] == 1


def test_pipeline_seeds_skill_memory(tmp_path: Path) -> None:
    f = tmp_path / "data.jsonl"
    _write_jsonl(f, [_make_event("Pesquisar documento")])
    memory = SkillMemory()
    pipeline = OfflinePipeline(skill_memory=memory)
    skills, _ = pipeline.run(f)
    assert len(skills) == 1
    assert len(memory._items) == 1


# Feature: enterprise-semantic-automation, Property 23: ImportReport com campos corretos
@given(
    n_valid=st.integers(min_value=0, max_value=10),
    n_noise=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_import_report_invariants(n_valid: int, n_noise: int, tmp_path: Path) -> None:
    import uuid
    unique_dir = tmp_path / uuid.uuid4().hex
    unique_dir.mkdir()
    f = unique_dir / "data.jsonl"
    events = [_make_event(f"Alvo {i}") for i in range(n_valid)]
    events += [_make_event(f"Ruído {i}", noise=True) for i in range(n_noise)]
    _write_jsonl(f, events)

    memory = SkillMemory()
    pipeline = OfflinePipeline(skill_memory=memory)
    _, report = pipeline.run(f)

    assert report["useful_events"] <= report["total_events"]
    assert report["skills_generated"] + report["skills_discarded"] == report["useful_events"]
