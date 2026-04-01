from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cil.text_utils import SimilarityMatcher, TextNormalizer


# ---------------------------------------------------------------------------
# TextNormalizer — testes unitários
# ---------------------------------------------------------------------------

def test_normalizer_lowercase():
    assert TextNormalizer.normalize("GED") == "ged"


def test_normalizer_removes_accents():
    assert TextNormalizer.normalize("Pesquisar") == "pesquisar"
    assert TextNormalizer.normalize("ação") == "acao"
    assert TextNormalizer.normalize("Excluir Pasta") == "excluir pasta"


def test_normalizer_collapses_spaces():
    assert TextNormalizer.normalize("  Pesquisar   documento  ") == "pesquisar documento"


def test_normalizer_empty_string():
    assert TextNormalizer.normalize("") == ""


# Feature: enterprise-semantic-automation, Property 17: TextNormalizer é idempotente
@given(s=st.text())
@settings(max_examples=100)
def test_normalizer_idempotent(s: str) -> None:
    once = TextNormalizer.normalize(s)
    twice = TextNormalizer.normalize(once)
    assert once == twice


# ---------------------------------------------------------------------------
# SimilarityMatcher — testes unitários
# ---------------------------------------------------------------------------

def test_similarity_identical_strings():
    assert SimilarityMatcher().score("Pesquisar", "Pesquisar") == 1.0


def test_similarity_case_insensitive():
    assert SimilarityMatcher().score("Pesquisar", "pesquisar") == 1.0


def test_similarity_accent_insensitive():
    assert SimilarityMatcher().score("ação", "acao") == 1.0


def test_similarity_partial_match():
    score = SimilarityMatcher().score("Excluir Pasta", "excluir pasta do ged")
    assert score > 0.6


def test_similarity_empty_strings():
    assert SimilarityMatcher().score("", "") == 1.0


def test_similarity_one_empty():
    assert SimilarityMatcher().score("texto", "") == 0.0


# Feature: enterprise-semantic-automation, Property 14: SimilarityMatcher é simétrico
@given(a=st.text(), b=st.text())
@settings(max_examples=100)
def test_similarity_symmetric(a: str, b: str) -> None:
    matcher = SimilarityMatcher()
    assert matcher.score(a, b) == matcher.score(b, a)


# Feature: enterprise-semantic-automation, Property 15: SimilarityMatcher retorna 1.0 para strings idênticas
@given(s=st.text())
@settings(max_examples=100)
def test_similarity_identity(s: str) -> None:
    assert SimilarityMatcher().score(s, s) == 1.0


# Feature: enterprise-semantic-automation, Property 16: SimilarityMatcher retorna float em [0.0, 1.0]
@given(a=st.text(), b=st.text())
@settings(max_examples=100)
def test_similarity_range(a: str, b: str) -> None:
    score = SimilarityMatcher().score(a, b)
    assert 0.0 <= score <= 1.0
