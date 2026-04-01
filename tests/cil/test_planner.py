from cil.planner import Planner
from contracts.screen_state import ScreenState, VisibleElementHint


def test_planner_prefers_search_target_when_objective_mentions_search():
    state = ScreenState(
        url="/ged",
        title="GED",
        primary_area="ged",
        visible_hints=[VisibleElementHint(kind="input", label="Pesquisar documento")],
    )

    intent = Planner().next_action(
        objective="Pesquisar documento no GED",
        state=state,
        history=[],
        known_skills=[],
    )

    assert intent.goal_type == "search"
    assert "pesquisar" in intent.semantic_target.lower()


# ---------------------------------------------------------------------------
# Testes de loop detection e regras adicionais
# ---------------------------------------------------------------------------

from hypothesis import given, settings
from hypothesis import strategies as st

from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.known_skill import KnownSkill


def _make_history(target: str, n: int) -> list[IntentAction]:
    return [
        IntentAction(
            intent_id=f"int_{i}",
            goal_type="navigate",
            semantic_target=target,
            expected_effect=ExpectedEffect(effect_type="screen_change", description="x"),
        )
        for i in range(n)
    ]


def test_planner_detects_loop_and_diverges():
    state = ScreenState(url="/ged", primary_area="ged")
    history = _make_history("Menu principal", 3)
    intent = Planner().next_action("Navegar", state, history, [])
    assert "loop_detected" in intent.reasoning_trace
    assert intent.semantic_target != "Menu principal"


def test_planner_no_loop_with_two_repetitions():
    state = ScreenState(url="/ged")
    history = _make_history("Menu principal", 2)
    intent = Planner().next_action("Pesquisar documento", state, history, [])
    assert "loop_detected" not in intent.reasoning_trace


def test_planner_fill_rule():
    state = ScreenState(url="/ged")
    intent = Planner().next_action("Preencher campo de nome", state, [], [])
    assert intent.goal_type == "fill"


def test_planner_confirm_rule():
    state = ScreenState(url="/ged")
    intent = Planner().next_action("Confirmar exclusão", state, [], [])
    assert intent.goal_type == "confirm"


def test_planner_save_rule():
    state = ScreenState(url="/ged")
    intent = Planner().next_action("Salvar registro", state, [], [])
    assert intent.goal_type == "save"


def test_planner_delete_rule():
    state = ScreenState(url="/ged")
    intent = Planner().next_action("Excluir documento", state, [], [])
    assert intent.goal_type == "delete"


def test_planner_empty_history_no_exception():
    state = ScreenState(url="/ged")
    intent = Planner().next_action("Pesquisar cliente", state, [], [])
    assert intent is not None
    assert intent.goal_type == "search"


def test_planner_prioritizes_highest_confidence_skill():
    state = ScreenState(url="/ged", primary_area="ged")
    skills = [
        KnownSkill(skill_id="s1", semantic_target="Pesquisar baixa", goal_type="search", confidence=0.5),
        KnownSkill(skill_id="s2", semantic_target="Pesquisar alta", goal_type="search", confidence=0.95),
    ]
    intent = Planner().next_action("Pesquisar documento", state, [], skills)
    assert intent.goal_type == "search"
    # A skill de maior confidence deve ser preferida
    assert intent.semantic_target == "Pesquisar alta"


# Feature: enterprise-semantic-automation, Property 11: Planner detecta loop e diverge o semantic_target
@given(target=st.text(min_size=1, max_size=30).filter(str.strip))
@settings(max_examples=50)
def test_property_loop_detection_diverges_target(target: str) -> None:
    state = ScreenState(url="/ged")
    history = _make_history(target.strip(), 3)
    intent = Planner().next_action("Navegar", state, history, [])
    assert "loop_detected" in intent.reasoning_trace
    assert intent.semantic_target != target.strip()


# Feature: enterprise-semantic-automation, Property 12: Planner prioriza skill de maior confidence
@given(
    low_conf=st.floats(min_value=0.1, max_value=0.5),
    high_conf=st.floats(min_value=0.8, max_value=0.99),
)
@settings(max_examples=50)
def test_property_planner_prioritizes_highest_confidence(low_conf: float, high_conf: float) -> None:
    state = ScreenState(url="/ged")
    skills = [
        KnownSkill(skill_id="s_low", semantic_target="Alvo baixo", goal_type="search", confidence=low_conf),
        KnownSkill(skill_id="s_high", semantic_target="Alvo alto", goal_type="search", confidence=high_conf),
    ]
    intent = Planner().next_action("Pesquisar documento", state, [], skills)
    assert intent.goal_type == "search"
    assert intent.semantic_target == "Alvo alto"
