from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.observed_action import ScreenSnapshot, StateChange
from runtime.effect_verifier import EffectVerifier


def _intent(effect_type: str) -> IntentAction:
    return IntentAction(
        intent_id="int_001",
        goal_type="search",
        semantic_target="Pesquisar",
        expected_effect=ExpectedEffect(effect_type=effect_type, description="x"),
    )


def _snap(**kwargs) -> ScreenSnapshot:
    defaults = {"url": "/ged", "title": "GED"}
    defaults.update(kwargs)
    return ScreenSnapshot(**defaults)


# ---------------------------------------------------------------------------
# Testes unitários básicos
# ---------------------------------------------------------------------------

def test_verifier_grid_refresh_confirmed():
    sc = StateChange(changed=True, change_type="grid_refresh")
    ok, msg = EffectVerifier().verify(_intent("grid_refresh"), _snap(), _snap(), state_change=sc)
    assert ok is True
    assert "grade" in msg.lower()


def test_verifier_toast_confirmed():
    sc = StateChange(changed=True, change_type="toast")
    ok, msg = EffectVerifier().verify(_intent("toast_visible"), _snap(), _snap(), state_change=sc)
    assert ok is True


def test_verifier_modal_open_confirmed():
    sc = StateChange(changed=True, change_type="modal_open")
    ok, _ = EffectVerifier().verify(_intent("modal_open"), _snap(), _snap(), state_change=sc)
    assert ok is True


def test_verifier_modal_close_confirmed():
    sc = StateChange(changed=True, change_type="modal_close")
    ok, _ = EffectVerifier().verify(_intent("modal_close"), _snap(), _snap(), state_change=sc)
    assert ok is True


def test_verifier_no_effect_returns_false():
    sc = StateChange(changed=False, change_type="none")
    ok, _ = EffectVerifier().verify(_intent("grid_refresh"), _snap(), _snap(), state_change=sc)
    assert ok is False


def test_verifier_derives_state_change_from_snapshots():
    before = _snap(url="/home")
    after = _snap(url="/ged")
    ok, msg = EffectVerifier().verify(_intent("screen_change"), before, after)
    assert ok is True


def test_verifier_derives_grid_refresh_from_snapshots():
    before = _snap(grid_row_count=5)
    after = _snap(grid_row_count=10)
    ok, _ = EffectVerifier().verify(_intent("grid_refresh"), before, after)
    assert ok is True


def test_verifier_derives_toast_from_snapshots():
    before = _snap(toast_present=False)
    after = _snap(toast_present=True)
    ok, _ = EffectVerifier().verify(_intent("toast_visible"), before, after)
    assert ok is True


# ---------------------------------------------------------------------------
# Feature: enterprise-semantic-automation, Property 9:
# EffectVerifier confirma grid_refresh e toast independente de URL/título
# ---------------------------------------------------------------------------

@given(
    url=st.text(max_size=30),
    title=st.text(max_size=30),
)
@settings(max_examples=100)
def test_property_grid_refresh_independent_of_url_title(url: str, title: str) -> None:
    sc = StateChange(changed=True, change_type="grid_refresh")
    snap = ScreenSnapshot(url=url, title=title)
    ok, _ = EffectVerifier().verify(_intent("grid_refresh"), snap, snap, state_change=sc)
    assert ok is True


@given(
    url=st.text(max_size=30),
    title=st.text(max_size=30),
)
@settings(max_examples=100)
def test_property_toast_independent_of_url_title(url: str, title: str) -> None:
    sc = StateChange(changed=True, change_type="toast")
    snap = ScreenSnapshot(url=url, title=title)
    ok, _ = EffectVerifier().verify(_intent("toast_visible"), snap, snap, state_change=sc)
    assert ok is True


# ---------------------------------------------------------------------------
# Feature: enterprise-semantic-automation, Property 10:
# EffectVerifier retorna False quando StateChange não corresponde ao efeito esperado
# ---------------------------------------------------------------------------

@given(
    effect=st.sampled_from(["grid_refresh", "toast_visible", "modal_open", "modal_close"]),
    change=st.sampled_from(["none"]),
)
@settings(max_examples=50)
def test_property_mismatch_returns_false(effect: str, change: str) -> None:
    sc = StateChange(changed=False, change_type=change)
    snap = ScreenSnapshot(url="/ged", title="GED")
    ok, _ = EffectVerifier().verify(_intent(effect), snap, snap, state_change=sc)
    assert ok is False
