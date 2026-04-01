from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from cil.observer import ScreenObserver


def _fp(url=None, title=None, modal=False, primary_area=None):
    return ScreenObserver()._build_fingerprint(url, title, modal, [], primary_area=primary_area)


# ---------------------------------------------------------------------------
# Testes unitários básicos
# ---------------------------------------------------------------------------

def test_fingerprint_basic():
    fp = _fp(url="/ged", title="GED")
    assert "ged" in fp


def test_fingerprint_strips_query_params():
    fp1 = _fp(url="/ged?t=123456")
    fp2 = _fp(url="/ged?t=999999")
    assert fp1 == fp2


def test_fingerprint_includes_primary_area():
    fp = _fp(url="/ged", title="GED", primary_area="financeiro")
    assert "financeiro" in fp


def test_fingerprint_none_url_stable():
    fp1 = _fp(url=None, title="GED")
    fp2 = _fp(url=None, title="GED")
    assert fp1 == fp2


def test_fingerprint_case_insensitive():
    fp1 = _fp(url="/GED", title="GED")
    fp2 = _fp(url="/ged", title="ged")
    assert fp1 == fp2


# Feature: enterprise-semantic-automation, Property 18: fingerprint estável sem query params
@given(
    base_url=st.text(min_size=1, max_size=30).filter(lambda s: "?" not in s),
    ts1=st.integers(min_value=0, max_value=999999),
    ts2=st.integers(min_value=0, max_value=999999),
)
@settings(max_examples=100)
def test_property_fingerprint_stable_without_query_params(base_url: str, ts1: int, ts2: int) -> None:
    fp1 = _fp(url=f"{base_url}?t={ts1}")
    fp2 = _fp(url=f"{base_url}?t={ts2}")
    assert fp1 == fp2


# Feature: enterprise-semantic-automation, Property 19: fingerprint inclui primary_area quando não-nulo
@given(area=st.text(min_size=1, max_size=20).filter(str.strip))
@settings(max_examples=100)
def test_property_fingerprint_includes_primary_area(area: str) -> None:
    from cil.text_utils import TextNormalizer
    fp = _fp(url="/ged", title="GED", primary_area=area.strip())
    assert TextNormalizer.normalize(area.strip()) in fp
