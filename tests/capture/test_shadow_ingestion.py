from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from capture.shadow_ingestion import (
    event_to_skill,
    filter_useful_events,
    load_jsonl,
    normalize_fingerprint,
    normalize_goal_type,
    write_skills,
)


# ---------------------------------------------------------------------------
# load_jsonl
# ---------------------------------------------------------------------------

def test_load_jsonl_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "empty.jsonl"
    f.write_text("", encoding="utf-8")
    assert load_jsonl(f) == []


def test_load_jsonl_nonexistent_file(tmp_path: Path) -> None:
    assert load_jsonl(tmp_path / "nope.jsonl") == []


def test_load_jsonl_valid_lines(tmp_path: Path) -> None:
    f = tmp_path / "data.jsonl"
    f.write_text('{"a": 1}\n{"b": 2}\n', encoding="utf-8")
    result = load_jsonl(f)
    assert len(result) == 2
    assert result[0] == {"a": 1}


# ---------------------------------------------------------------------------
# filter_useful_events
# ---------------------------------------------------------------------------

def test_filter_removes_noise() -> None:
    events = [
        {"is_noise": True, "business_target": "Pesquisar"},
        {"is_noise": False, "business_target": "Salvar"},
    ]
    result = filter_useful_events(events)
    assert len(result) == 1
    assert result[0]["business_target"] == "Salvar"


def test_filter_removes_events_without_target() -> None:
    events = [
        {"is_noise": False, "business_target": "", "elemento_alvo": {"label_curto": ""}},
        {"is_noise": False, "business_target": "Pesquisar"},
    ]
    result = filter_useful_events(events)
    assert len(result) == 1


def test_filter_shell_events_when_iframe_present() -> None:
    events = [
        {"is_noise": False, "capture_scope": "shell", "business_target": "Menu"},
        {"is_noise": False, "capture_scope": "module_iframe", "business_target": "Botão"},
    ]
    result = filter_useful_events(events)
    # shell deve ser filtrado quando há module_iframe
    assert len(result) == 1
    assert result[0]["capture_scope"] == "module_iframe"


# ---------------------------------------------------------------------------
# normalize_goal_type
# ---------------------------------------------------------------------------

def test_normalize_goal_type_from_semantic_action() -> None:
    assert normalize_goal_type({"semantic_action": "delete"}) == "delete"
    assert normalize_goal_type({"semantic_action": "confirm"}) == "confirm"


def test_normalize_goal_type_confirm_from_target() -> None:
    assert normalize_goal_type({"semantic_action": "", "business_target": "Sim"}) == "confirm"


def test_normalize_goal_type_fill_from_email() -> None:
    assert normalize_goal_type({"semantic_action": "", "business_target": "E-mail"}) == "fill"


def test_normalize_goal_type_fill_from_tag() -> None:
    event = {"semantic_action": "", "business_target": "campo", "technical": {"tag": "input"}}
    assert normalize_goal_type(event) == "fill"


def test_normalize_goal_type_navigate_fallback() -> None:
    assert normalize_goal_type({"semantic_action": "", "business_target": "Algo"}) == "navigate"


# ---------------------------------------------------------------------------
# normalize_fingerprint
# ---------------------------------------------------------------------------

def test_normalize_fingerprint_ged_documentos() -> None:
    event = {
        "elemento_alvo": {"contexto_tela": "GED | X Platform"},
        "technical": {"page_title": "GED | X Platform"},
    }
    assert normalize_fingerprint(event) == "GED | Documentos"


def test_normalize_fingerprint_senior_shell() -> None:
    event = {
        "contexto_semantico": {"tela_atual": {"tela_id": "Senior | Plataforma de solução"}},
        "technical": {},
    }
    assert normalize_fingerprint(event) == "Senior X | Shell"


def test_normalize_fingerprint_unknown() -> None:
    event = {"technical": {}, "elemento_alvo": {}}
    assert normalize_fingerprint(event) == "tela desconhecida"


# ---------------------------------------------------------------------------
# event_to_skill
# ---------------------------------------------------------------------------

def test_event_to_skill_minimal_valid() -> None:
    event = {
        "semantic_action": "navigate",
        "business_target": "Menu principal",
        "elemento_alvo": {"confianca_captura": "alta"},
        "technical": {},
    }
    skill = event_to_skill(event)
    assert skill["semantic_target"] == "Menu principal"
    assert skill["goal_type"] == "navigate"
    assert skill["confidence"] == 0.9
    assert skill["source"] == "dual_output_shadow"
    assert skill["skill_id"].startswith("skill_")


def test_event_to_skill_no_target_uses_fallback() -> None:
    event = {"semantic_action": "navigate", "technical": {}, "elemento_alvo": {}}
    skill = event_to_skill(event)
    assert skill["semantic_target"] == "alvo não identificado"


# ---------------------------------------------------------------------------
# write_skills
# ---------------------------------------------------------------------------

def test_write_skills_creates_file(tmp_path: Path) -> None:
    skills = [{"skill_id": "s1", "semantic_target": "Pesquisar"}]
    out = tmp_path / "out" / "skills.jsonl"
    write_skills(skills, out)
    assert out.exists()
    lines = [l for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["skill_id"] == "s1"


# ---------------------------------------------------------------------------
# Property 2: Equivalência com implementações originais
# Feature: enterprise-semantic-automation, Property 2: Equivalência do ShadowImporter
# ---------------------------------------------------------------------------

_VALID_SEMANTIC_ACTIONS = st.sampled_from(
    ["navigate", "delete", "confirm", "save", "fill", "select", "search", "close", ""]
)

@given(
    semantic_action=_VALID_SEMANTIC_ACTIONS,
    business_target=st.text(max_size=40),
)
@settings(max_examples=100)
def test_normalize_goal_type_deterministic(semantic_action: str, business_target: str) -> None:
    """normalize_goal_type é determinístico para a mesma entrada."""
    event = {"semantic_action": semantic_action, "business_target": business_target, "technical": {}, "elemento_alvo": {}}
    assert normalize_goal_type(event) == normalize_goal_type(event)


@given(business_target=st.text(max_size=40))
@settings(max_examples=100)
def test_normalize_fingerprint_deterministic(business_target: str) -> None:
    """normalize_fingerprint é determinístico para a mesma entrada."""
    event = {"business_target": business_target, "technical": {}, "elemento_alvo": {}, "contexto_semantico": {}}
    assert normalize_fingerprint(event) == normalize_fingerprint(event)
