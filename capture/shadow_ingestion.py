"""ShadowImporter — módulo unificado de importação de shadow exports.

Substitui o código duplicado entre scripts/import_dual_output_shadow.py
e scripts/test_dual_output_shadow_v2.py. Todos os scripts devem importar
daqui em vez de reimplementar estas funções.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4


def _compact(text: str | None) -> str:
    """Remove espaços extras e faz strip. Função interna."""
    return " ".join((text or "").split()).strip()


def load_jsonl(path: Path) -> list[dict]:
    """Carrega todas as linhas de um arquivo JSONL como lista de dicts."""
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def filter_useful_events(events: list[dict]) -> list[dict]:
    """Filtra eventos de ruído e sem alvo identificável.

    Para o Tutorial Player, preserva eventos de shell também quando
    eles têm business_target válido — são passos de navegação importantes.
    """
    filtered: list[dict] = []
    for e in events:
        if e.get("is_noise", False):
            continue
        if not _compact(e.get("business_target")) and not _compact(
            e.get("elemento_alvo", {}).get("label_curto")
        ):
            continue
        filtered.append(e)
    return filtered


def normalize_goal_type(event: dict) -> str:
    """Normaliza o tipo de ação semântica de um evento bruto."""
    semantic_action = _compact(event.get("semantic_action")).lower()
    target = (
        _compact(event.get("business_target"))
        or _compact(event.get("elemento_alvo", {}).get("label_curto"))
        or _compact(event.get("elemento_alvo", {}).get("descricao_visual"))
        or _compact(event.get("technical", {}).get("text_hint"))
    ).lower()
    tech = event.get("technical", {}) or {}
    raw_action = _compact(event.get("acao")).lower()
    selector = _compact(
        tech.get("seletor_css") or event.get("elemento_alvo", {}).get("seletor_hint")
    ).lower()
    tag = _compact(
        tech.get("tag") or event.get("elemento_alvo", {}).get("tipo_elemento")
    ).lower()
    pattern = _compact(event.get("pattern_detectado")).lower()

    if semantic_action in {"delete", "confirm", "save", "fill", "select", "search", "close"}:
        return semantic_action

    if target in {"sim", "confirmar", "ok", "yes", "aceitar"}:
        return "confirm"
    if any(k in target for k in ["e-mail", "email", "@"]):
        return "fill"
    if tag in {"input", "textarea"}:
        return "fill"
    if raw_action == "preencher_campo":
        return "fill"
    if raw_action == "selecionar_opcao":
        return "select"
    if raw_action == "clique_direito":
        return "open"
    if "coletar assinaturas" in target:
        return "open"
    if "nova pasta" in target:
        return "open"
    if "assinar" in target:
        return "select"
    if pattern in {"form_fill"}:
        return "fill"
    if pattern in {"menu_navigation", "breadcrumb_navigation"}:
        return "navigate"
    if selector.startswith("[name="):
        return "fill"

    return semantic_action or "navigate"


def normalize_fingerprint(event: dict) -> str:
    """Normaliza o fingerprint de tela de um evento bruto."""
    text = " | ".join(
        [
            _compact(event.get("elemento_alvo", {}).get("contexto_tela")),
            _compact(
                event.get("contexto_semantico", {}).get("tela_atual", {}).get("tela_id")
            ),
            _compact(event.get("technical", {}).get("page_title")),
            _compact(event.get("technical", {}).get("url_hint")),
            _compact(event.get("business_target")),
            _compact(event.get("elemento_alvo", {}).get("label_curto")),
        ]
    ).lower()

    if "coletar assinaturas" in text:
        return "GED | Coletar Assinaturas"
    if "financeiro" in text:
        return "GED | Financeiro"
    if (
        "documentos" in text
        or "gerenciamento de documentos" in text
        or "ged | x platform" in text
    ):
        return "GED | Documentos"
    if "senior | plataforma de solução" in text or "senior x platform" in text:
        return "Senior X | Shell"
    return (
        _compact(event.get("technical", {}).get("page_title"))
        or _compact(event.get("elemento_alvo", {}).get("contexto_tela"))
        or "tela desconhecida"
    )


def event_to_skill(event: dict) -> dict:
    """Converte um evento bruto de shadow em um dict compatível com KnownSkill."""
    target = (
        _compact(event.get("business_target"))
        or _compact(event.get("elemento_alvo", {}).get("label_curto"))
        or _compact(event.get("elemento_alvo", {}).get("descricao_visual"))
        or _compact(event.get("technical", {}).get("text_hint"))
        or "alvo não identificado"
    )
    goal_type = normalize_goal_type(event)
    fp = normalize_fingerprint(event)
    selector = (
        _compact(event.get("technical", {}).get("seletor_css"))
        or _compact(event.get("elemento_alvo", {}).get("seletor_hint"))
        or None
    )
    iframe = event.get("technical", {}).get("iframe_hint") or event.get(
        "elemento_alvo", {}
    ).get("iframe_hint") or None

    confidence_map = {"alta": 0.9, "media": 0.7, "baixa": 0.45}
    conf = confidence_map.get(
        _compact(event.get("elemento_alvo", {}).get("confianca_captura")).lower(),
        0.7,
    )

    return {
        "skill_id": f"skill_{uuid4().hex[:12]}",
        "semantic_target": target,
        "goal_type": goal_type,
        "screen_fingerprint": fp,
        "preferred_selector": selector,
        "preferred_iframe": iframe,
        "confidence": conf,
        "source": "dual_output_shadow",
    }


def write_skills(skills: list[dict], out_path: Path) -> None:
    """Grava lista de skills em arquivo JSONL."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for skill in skills:
            f.write(json.dumps(skill, ensure_ascii=False) + "\n")
