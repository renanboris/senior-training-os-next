from cil.skill_memory import SkillMemory
from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.known_skill import KnownSkill
from contracts.screen_state import ScreenState


def test_skill_memory_retrieves_matching_skill():
    memory = SkillMemory()
    memory.seed([
        KnownSkill(
            skill_id="skill_001",
            semantic_target="Pesquisar documento",
            goal_type="search",
            screen_fingerprint="ged_fingerprint",
            confidence=0.91,
        )
    ])

    state = ScreenState(fingerprint="ged_fingerprint")
    intent = IntentAction(
        intent_id="int_001",
        goal_type="search",
        semantic_target="Pesquisar documento",
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="Atualiza a grade"),
    )

    matches = memory.retrieve(state, intent)

    assert len(matches) == 1
    assert matches[0].skill_id == "skill_001"


# ---------------------------------------------------------------------------
# Testes de persistência — JsonlSkillBackend
# ---------------------------------------------------------------------------

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from cil.skill_memory import JsonlSkillBackend
from contracts.execution_result import ExecutionResult


def _make_skill(skill_id: str = "skill_001", target: str = "Pesquisar", goal: str = "search") -> KnownSkill:
    return KnownSkill(skill_id=skill_id, semantic_target=target, goal_type=goal, confidence=0.8)


def test_jsonl_backend_load_nonexistent_file(tmp_path: Path) -> None:
    backend = JsonlSkillBackend(tmp_path / "nope.jsonl")
    assert backend.load() == []


def test_jsonl_backend_save_and_load(tmp_path: Path) -> None:
    backend = JsonlSkillBackend(tmp_path / "skills.jsonl")
    skills = [_make_skill("s1"), _make_skill("s2", "Salvar", "save")]
    backend.save(skills)
    loaded = backend.load()
    assert {s.skill_id for s in loaded} == {"s1", "s2"}


def test_jsonl_backend_ignores_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "skills.jsonl"
    path.write_text('{"skill_id":"s1","semantic_target":"x","goal_type":"search","confidence":0.8,"source":"test"}\nNOT_JSON\n', encoding="utf-8")
    backend = JsonlSkillBackend(path)
    loaded = backend.load()
    assert len(loaded) == 1
    assert loaded[0].skill_id == "s1"


# Feature: enterprise-semantic-automation, Property 3: Round-trip de persistência do SkillMemory
@given(
    targets=st.lists(
        st.text(min_size=1, max_size=30).filter(str.strip),
        min_size=0,
        max_size=10,
        unique=True,
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_skill_backend_round_trip(targets: list[str], tmp_path: Path) -> None:
    import uuid
    backend = JsonlSkillBackend(tmp_path / uuid.uuid4().hex / "skills.jsonl")
    skills = [_make_skill(f"skill_{i}", t) for i, t in enumerate(targets)]
    backend.save(skills)
    loaded = backend.load()
    assert {s.skill_id for s in loaded} == {s.skill_id for s in skills}


# Feature: enterprise-semantic-automation, Property 4: SkillMemory chama backend.load() na inicialização
def test_property_skill_memory_loads_on_init(tmp_path: Path) -> None:
    backend = JsonlSkillBackend(tmp_path / "skills.jsonl")
    skill = _make_skill("s_init", "Pesquisar documento")
    backend.save([skill])

    memory = SkillMemory(backend=backend)
    state = ScreenState(fingerprint=None)
    intent = IntentAction(
        intent_id="int_x",
        goal_type="search",
        semantic_target="Pesquisar documento",
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="x"),
    )
    matches = memory.retrieve(state, intent)
    assert any(m.skill_id == "s_init" for m in matches)


# Feature: enterprise-semantic-automation, Property 5: SkillMemory chama backend.save() após learn()
def test_property_skill_memory_saves_after_learn(tmp_path: Path) -> None:
    backend = JsonlSkillBackend(tmp_path / "skills.jsonl")
    memory = SkillMemory(backend=backend)

    intent = IntentAction(
        intent_id="int_learn",
        goal_type="search",
        semantic_target="Novo alvo aprendido",
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="x"),
    )
    result = ExecutionResult(
        execution_id="exe_001",
        intent_id="int_learn",
        resolution_id="res_001",
        status="success",
    )
    skill = memory.learn(intent, result, preferred_selector='role=button[name="Pesquisar"]')
    assert skill is not None

    # Verifica que foi persistido
    loaded = backend.load()
    assert any(s.skill_id == skill.skill_id for s in loaded)


def test_skill_memory_no_learn_on_failure() -> None:
    memory = SkillMemory()
    intent = IntentAction(
        intent_id="int_fail",
        goal_type="search",
        semantic_target="Alvo",
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="x"),
    )
    result = ExecutionResult(
        execution_id="exe_001",
        intent_id="int_fail",
        resolution_id="res_001",
        status="failed",
    )
    assert memory.learn(intent, result) is None


def test_skill_memory_deduplication() -> None:
    memory = SkillMemory()
    memory.seed([_make_skill("s_existing", "Pesquisar documento")])

    intent = IntentAction(
        intent_id="int_dup",
        goal_type="search",
        semantic_target="Pesquisar documento",
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="x"),
    )
    result = ExecutionResult(
        execution_id="exe_001",
        intent_id="int_dup",
        resolution_id="res_001",
        status="success",
    )
    # Não deve aprender skill duplicada
    learned = memory.learn(intent, result)
    assert learned is None
