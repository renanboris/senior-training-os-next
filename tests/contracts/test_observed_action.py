from datetime import datetime, timezone

from contracts.observed_action import ObservedAction, RawTarget, ScreenSnapshot


def test_observed_action_minimum_contract():
    item = ObservedAction(
        event_id="obs_001",
        timestamp=datetime.now(timezone.utc),
        action_type="click",
        raw_target=RawTarget(text="Pesquisar"),
        screen_before=ScreenSnapshot(url="/ged", title="GED"),
    )

    assert item.event_id == "obs_001"
    assert item.raw_target.text == "Pesquisar"
    assert item.capture_confidence == 0.5
    assert item.risk_class == "low"