import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.observed_action import ObservedAction, RawTarget, ScreenSnapshot
from contracts.screen_state import ScreenState, VisibleElementHint


@pytest.fixture
def sample_observed_action() -> ObservedAction:
    return ObservedAction(
        event_id="obs_fixture_001",
        timestamp=datetime.now(timezone.utc),
        action_type="click",
        raw_target=RawTarget(text="Pesquisar", aria_label="Pesquisar documento"),
        screen_before=ScreenSnapshot(url="/ged", title="GED"),
        capture_confidence=0.9,
    )


@pytest.fixture
def sample_screen_state() -> ScreenState:
    return ScreenState(
        url="/ged",
        title="GED | Documentos",
        fingerprint="ged::ged | documentos::modal=0::ged::",
        primary_area="ged",
        visible_hints=[
            VisibleElementHint(kind="button", label="Pesquisar"),
            VisibleElementHint(kind="input", label="campo de busca"),
        ],
    )


@pytest.fixture
def sample_intent_action() -> IntentAction:
    return IntentAction(
        intent_id="int_fixture_001",
        goal_type="search",
        semantic_target="Pesquisar documento",
        expected_effect=ExpectedEffect(
            effect_type="grid_refresh",
            description="A grade deve ser atualizada após a pesquisa.",
        ),
        semantic_confidence=0.85,
    )


@pytest.fixture
def shadow_jsonl_fixture(tmp_path: Path) -> Path:
    """Cria arquivo .jsonl temporário com 3 eventos válidos e 1 is_noise=True."""
    events = [
        {
            "semantic_action": "navigate",
            "business_target": "Menu principal Senior Flow",
            "is_noise": False,
            "capture_scope": "module_iframe",
            "elemento_alvo": {"confianca_captura": "alta", "label_curto": "Menu principal Senior Flow"},
            "technical": {"page_title": "GED | X Platform"},
        },
        {
            "semantic_action": "open",
            "business_target": "Financeiro",
            "is_noise": False,
            "capture_scope": "module_iframe",
            "elemento_alvo": {"confianca_captura": "media"},
            "technical": {},
        },
        {
            "semantic_action": "fill",
            "business_target": "E-mail",
            "is_noise": False,
            "capture_scope": "module_iframe",
            "elemento_alvo": {"confianca_captura": "alta"},
            "technical": {"tag": "input"},
        },
        {
            "semantic_action": "navigate",
            "business_target": "Ruído",
            "is_noise": True,
            "capture_scope": "shell",
            "elemento_alvo": {},
            "technical": {},
        },
    ]
    path = tmp_path / "fixture_shadow.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return path
