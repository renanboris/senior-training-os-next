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