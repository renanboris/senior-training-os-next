"""Testes de integração end-to-end do OfflinePipeline.

Usa fixture shadow_jsonl_fixture para exercitar o pipeline completo.
Deve completar em < 2s.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cil.skill_memory import JsonlSkillBackend, SkillMemory
from orchestration.offline_pipeline import OfflinePipeline


def test_offline_pipeline_e2e_with_fixture(shadow_jsonl_fixture: Path, tmp_path: Path):
    """Exercita OfflinePipeline.run() com arquivo real e verifica persistência."""
    backend = JsonlSkillBackend(tmp_path / "skills.jsonl")
    memory = SkillMemory(backend=backend)
    pipeline = OfflinePipeline(skill_memory=memory)

    skills, report = pipeline.run(shadow_jsonl_fixture)

    # 3 eventos válidos (1 noise filtrado)
    assert report["total_events"] == 4
    assert report["useful_events"] == 3
    assert report["skills_generated"] == 3
    assert report["skills_discarded"] == 0

    # Skills persistidas no backend
    loaded = backend.load()
    assert len(loaded) == 3

    # Todos os skill_ids são únicos
    ids = [s.skill_id for s in loaded]
    assert len(set(ids)) == 3


def test_offline_pipeline_e2e_report_invariant(shadow_jsonl_fixture: Path, tmp_path: Path):
    """Verifica invariante: skills_generated + skills_discarded == useful_events."""
    memory = SkillMemory()
    pipeline = OfflinePipeline(skill_memory=memory)
    _, report = pipeline.run(shadow_jsonl_fixture)
    assert report["skills_generated"] + report["skills_discarded"] == report["useful_events"]
    assert report["useful_events"] <= report["total_events"]
