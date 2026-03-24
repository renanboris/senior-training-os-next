from capture.state_diff import StateDiffEngine


def test_state_diff_detects_navigation():
    before = {"url": "/home", "title": "Home", "modal_open": False}
    after = {"url": "/ged", "title": "GED", "modal_open": False}

    diff = StateDiffEngine().detect(before, after)

    assert diff.changed is True
    assert diff.change_type == "navigation"