from capture.event_normalizer import EventNormalizer


def test_event_normalizer_builds_observed_action():
    raw_event = {
        "action_type": "type_and_enter",
        "text": "Pesquisar",
        "typed_value": "nota fiscal",
        "screen_before": {"url": "/ged", "title": "GED"},
        "screen_after": {"url": "/ged", "title": "GED"},
        "capture_confidence": 0.87,
    }

    item = EventNormalizer().normalize(raw_event)

    assert item.action_type == "type_and_enter"
    assert item.raw_target.text == "Pesquisar"
    assert item.typed_value == "nota fiscal"
    assert item.capture_confidence == 0.87