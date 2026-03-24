from datetime import datetime, timezone

from cil.interpreter import IntentInterpreter
from contracts.observed_action import ObservedAction, RawTarget, ScreenSnapshot, StateChange
from contracts.screen_state import ScreenState


def test_interpreter_maps_search_intent_from_type_and_enter():
    observed = ObservedAction(
        event_id="obs_001",
        timestamp=datetime.now(timezone.utc),
        action_type="type_and_enter",
        raw_target=RawTarget(text="Pesquisar"),
        typed_value="cliente ACME",
        screen_before=ScreenSnapshot(url="/ged", title="GED"),
        state_change=StateChange(changed=True, change_type="grid_refresh"),
        capture_confidence=0.9,
    )
    state = ScreenState(url="/ged", title="GED", primary_area="ged")

    intent = IntentInterpreter().interpret(observed, state)

    assert intent.goal_type == "search"
    assert intent.semantic_target == "Pesquisar"
    assert intent.business_entity == "cliente"
    assert intent.semantic_confidence >= 0.8