from hypothesis import given, settings
from hypothesis import strategies as st

from capture.state_diff import StateDiffEngine


def test_state_diff_detects_navigation():
    before = {"url": "/home", "title": "Home", "modal_open": False}
    after = {"url": "/ged", "title": "GED", "modal_open": False}

    diff = StateDiffEngine().detect(before, after)

    assert diff.changed is True
    assert diff.change_type == "navigation"


def test_state_diff_detects_modal_open():
    before = {"url": "/ged", "modal_open": False}
    after = {"url": "/ged", "modal_open": True}
    diff = StateDiffEngine().detect(before, after)
    assert diff.changed is True
    assert diff.change_type == "modal_open"


def test_state_diff_detects_modal_close():
    before = {"url": "/ged", "modal_open": True}
    after = {"url": "/ged", "modal_open": False}
    diff = StateDiffEngine().detect(before, after)
    assert diff.changed is True
    assert diff.change_type == "modal_close"


def test_state_diff_detects_toast():
    before = {"url": "/ged", "toast_present": False}
    after = {"url": "/ged", "toast_present": True}
    diff = StateDiffEngine().detect(before, after)
    assert diff.changed is True
    assert diff.change_type == "toast"


def test_state_diff_detects_grid_refresh():
    before = {"url": "/ged", "grid_row_count": 5}
    after = {"url": "/ged", "grid_row_count": 10}
    diff = StateDiffEngine().detect(before, after)
    assert diff.changed is True
    assert diff.change_type == "grid_refresh"


def test_state_diff_no_change():
    snap = {"url": "/ged", "title": "GED", "modal_open": False, "grid_row_count": 5, "toast_present": False}
    diff = StateDiffEngine().detect(snap, snap)
    assert diff.changed is False
    assert diff.change_type == "none"


# Feature: enterprise-semantic-automation, Property 6: detecta toast quando presente apenas no after
@given(url=st.text(min_size=1, max_size=30))
@settings(max_examples=100)
def test_property_toast_detected_only_in_after(url: str) -> None:
    before = {"url": url, "toast_present": False}
    after = {"url": url, "toast_present": True}
    diff = StateDiffEngine().detect(before, after)
    assert diff.changed is True
    assert diff.change_type == "toast"


# Feature: enterprise-semantic-automation, Property 7: detecta grid_refresh quando grid_row_count difere
@given(n=st.integers(min_value=0, max_value=1000), m=st.integers(min_value=0, max_value=1000))
@settings(max_examples=100)
def test_property_grid_refresh_when_count_differs(n: int, m: int) -> None:
    if n == m:
        return
    before = {"grid_row_count": n}
    after = {"grid_row_count": m}
    diff = StateDiffEngine().detect(before, after)
    assert diff.changed is True
    assert diff.change_type == "grid_refresh"


# Feature: enterprise-semantic-automation, Property 8: snapshots idênticos retornam none
@given(
    url=st.text(max_size=30),
    title=st.text(max_size=30),
    modal=st.booleans(),
    grid=st.integers(min_value=0, max_value=100),
    toast=st.booleans(),
)
@settings(max_examples=100)
def test_property_identical_snapshots_return_none(url, title, modal, grid, toast) -> None:
    snap = {"url": url, "title": title, "modal_open": modal, "grid_row_count": grid, "toast_present": toast}
    diff = StateDiffEngine().detect(snap, snap)
    assert diff.changed is False
    assert diff.change_type == "none"