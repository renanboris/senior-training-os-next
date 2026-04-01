from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import strategies as st

from contracts.execution_result import ExecutionResult
from contracts.resolved_target import ResolvedNode, ResolvedTarget


def shadow_event_strategy():
    """Hypothesis strategy que gera shadow events válidos."""
    return st.fixed_dictionaries({
        "id_acao": st.integers(min_value=1, max_value=999),
        "business_target": st.text(min_size=1, max_size=40),
        "semantic_action": st.sampled_from(["navigate", "fill", "confirm", "save", "open", "select"]),
        "micro_narracao": st.text(max_size=100),
        "is_noise": st.just(False),
        "capture_scope": st.just("module_iframe"),
        "acao": st.sampled_from(["clique", "digitar", "selecionar"]),
        "valor_input": st.one_of(st.none(), st.text(max_size=30)),
        "elemento_alvo": st.fixed_dictionaries({
            "confianca_captura": st.sampled_from(["alta", "media", "baixa"]),
            "label_curto": st.text(max_size=30),
            "seletor_hint": st.one_of(st.none(), st.text(max_size=50)),
            "iframe_hint": st.one_of(st.none(), st.text(max_size=30)),
            "tipo_elemento": st.sampled_from(["button", "input", "a", "span"]),
            "coordenadas_relativas": st.fixed_dictionaries({
                "x_pct": st.floats(0.0, 1.0, allow_nan=False),
                "y_pct": st.floats(0.0, 1.0, allow_nan=False),
                "w_pct": st.floats(0.0, 0.5, allow_nan=False),
                "h_pct": st.floats(0.0, 0.5, allow_nan=False),
            }),
        }),
        "contexto_semantico": st.fixed_dictionaries({
            "tela_atual": st.fixed_dictionaries({
                "tela_id": st.text(max_size=40),
                "url": st.one_of(
                    st.none(),
                    st.just("https://platform-homologx.senior.com.br/tecnologia/platform/senior-x/#/"),
                ),
                "iframe": st.none(),
                "scope": st.just("shell"),
            }),
        }),
    })


@pytest.fixture
def sample_shadow_event() -> dict:
    return {
        "id_acao": 1,
        "business_target": "Financeiro",
        "semantic_action": "navigate",
        "micro_narracao": "Navegar para a seção Financeiro do GED.",
        "is_noise": False,
        "capture_scope": "module_iframe",
        "acao": "clique",
        "valor_input": "",
        "elemento_alvo": {
            "confianca_captura": "alta",
            "label_curto": "Financeiro",
            "seletor_hint": "[data-label='Financeiro']",
            "iframe_hint": None,
            "tipo_elemento": "button",
            "coordenadas_relativas": {"x_pct": 0.1, "y_pct": 0.3, "w_pct": 0.05, "h_pct": 0.04},
        },
        "contexto_semantico": {
            "tela_atual": {
                "tela_id": "GED | Documentos",
                "url": "https://platform-homologx.senior.com.br/tecnologia/platform/senior-x/#/ged",
                "iframe": None,
                "scope": "shell",
            }
        },
    }


@pytest.fixture
def mock_page():
    page = MagicMock()
    page.url = "https://platform-homologx.senior.com.br/tecnologia/platform/senior-x/#/"
    page.title = AsyncMock(return_value="Senior X")
    page.evaluate = AsyncMock(return_value=None)
    page.goto = AsyncMock(return_value=None)
    page.frames = []
    page.locator = MagicMock(return_value=MagicMock(
        count=AsyncMock(return_value=0),
        click=AsyncMock(return_value=None),
        fill=AsyncMock(return_value=None),
    ))
    page.mouse = MagicMock(click=AsyncMock(return_value=None))
    page.wait_for_load_state = AsyncMock(return_value=None)
    page.get_by_role = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
    page.get_by_label = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
    page.get_by_placeholder = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
    return page


@pytest.fixture
def shadow_jsonl_fixture(tmp_path: Path) -> Path:
    events = [
        {
            "id_acao": i,
            "business_target": f"Alvo {i}",
            "semantic_action": "navigate",
            "micro_narracao": f"Passo {i}",
            "is_noise": False,
            "capture_scope": "module_iframe",
            "acao": "clique",
            "valor_input": "",
            "elemento_alvo": {
                "confianca_captura": "alta",
                "label_curto": f"Alvo {i}",
                "seletor_hint": None,
                "iframe_hint": None,
                "tipo_elemento": "button",
                "coordenadas_relativas": {"x_pct": 0.1 * i, "y_pct": 0.2, "w_pct": 0.05, "h_pct": 0.04},
            },
            "contexto_semantico": {
                "tela_atual": {
                    "tela_id": "GED",
                    "url": "https://platform-homologx.senior.com.br/tecnologia/platform/senior-x/#/",
                    "iframe": None,
                    "scope": "shell",
                }
            },
        }
        for i in range(1, 4)
    ]
    path = tmp_path / "fixture.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return path


def make_fake_resolver(strategy: str = "coordinates"):
    """Cria um resolver mock que sempre resolve com sucesso."""
    resolver = MagicMock()
    resolved = ResolvedTarget(
        resolution_id="res_test",
        intent_id="int_test",
        strategy_used=strategy,
        resolved_target=ResolvedNode(selector=None),
        resolution_confidence=0.8,
    )
    trace = type("T", (), {"steps": ["fake"]})()
    resolver.resolve = AsyncMock(return_value=(resolved, trace))
    return resolver


def make_failing_resolver():
    """Cria um resolver mock que sempre falha."""
    resolver = MagicMock()
    resolver.resolve = AsyncMock(side_effect=RuntimeError("all strategies failed"))
    return resolver


def make_fake_executor(status: str = "success"):
    """Cria um executor mock."""
    executor = MagicMock()
    executor.execute = AsyncMock(return_value=ExecutionResult(
        execution_id="exe_test",
        intent_id="int_test",
        resolution_id="res_test",
        status=status,
    ))
    return executor
