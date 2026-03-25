from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.known_skill import KnownSkill

INPUT_DIR = ROOT / "data" / "legacy" / "raw_json"
OUTPUT_SKILLS = ROOT / "data" / "legacy" / "imported_skills.jsonl"
OUTPUT_REVIEW = ROOT / "data" / "legacy" / "needs_review.jsonl"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def iter_steps(payload):
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return

    if isinstance(payload, dict):
        if isinstance(payload.get("passos"), list):
            for item in payload["passos"]:
                if isinstance(item, dict):
                    yield item
            return
        yield payload


def first_non_empty(*values):
    for v in values:
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def extract_main_action(step: dict) -> dict:
    actions = step.get("acoes_tecnicas")
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, dict):
                return action
    return {}


def extract_element_target(action: dict) -> dict:
    value = action.get("elemento_alvo")
    if isinstance(value, dict):
        return value
    return {}


def extract_quoted_label(text: str | None) -> str | None:
    if not text:
        return None

    # pega coisas como: Botão 'Excluir' / pasta "Logistica"
    patterns = [
        r"'([^']+)'",
        r'"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            label = match.group(1).strip()
            if label:
                return label
    return None


def infer_goal_type(step: dict, file_name: str = "") -> str:
    action = extract_main_action(step)

    blob = " ".join(
        filter(
            None,
            [
                file_name,
                str(step.get("tipo_passo", "")),
                str(step.get("pedagogia", {}).get("tooltip_dap", "")),
                str(step.get("pedagogia", {}).get("ancora", "")),
                str(action.get("acao", "")),
                str(action.get("intencao_semantica", "")),
                json.dumps(step, ensure_ascii=False),
            ],
        )
    ).lower()

    if "concluir_video" in blob:
        return "navigate"

    if any(k in blob for k in ["pesquisar", "buscar", "filtrar", "filtro"]):
        return "search"
    if any(k in blob for k in ["salvar", "gravar"]):
        return "save"
    if "confirm" in blob or "confirmação" in blob or "confirmar" in blob:
        return "confirm"
    if any(k in blob for k in ["excluir", "remover", "apagar", "deletar", "lixeira", "restaurar"]):
        if "restaurar" in blob:
            return "open"
        return "delete"
    if any(k in blob for k in ["abrir", "visualizar", "detalhar", "duplo_clique"]):
        return "open"
    if any(k in blob for k in ["digitar", "preencher", "input"]):
        return "fill"
    return "navigate"


def extract_semantic_target(step: dict) -> str:
    action = extract_main_action(step)
    element = extract_element_target(action)
    pedagogia = step.get("pedagogia", {}) if isinstance(step.get("pedagogia"), dict) else {}

    tooltip = first_non_empty(pedagogia.get("tooltip_dap"))
    quoted_tooltip = extract_quoted_label(tooltip)

    quoted_intention = extract_quoted_label(first_non_empty(action.get("intencao_semantica")))
    quoted_anchor = extract_quoted_label(first_non_empty(pedagogia.get("ancora")))

    target = first_non_empty(
        quoted_tooltip,
        quoted_intention,
        quoted_anchor,
        tooltip,
        element.get("descricao_visual"),
        action.get("intencao_semantica"),
        pedagogia.get("ancora"),
        step.get("tipo_passo"),
    )

    return target or "alvo não identificado"


def extract_selector(step: dict) -> str | None:
    action = extract_main_action(step)
    element = extract_element_target(action)

    return first_non_empty(
        action.get("seletor_css"),
        action.get("selector"),
        element.get("seletor_css"),
        element.get("selector"),
    )


def extract_iframe(step: dict) -> str | None:
    action = extract_main_action(step)
    element = extract_element_target(action)

    return first_non_empty(
        action.get("iframe"),
        element.get("iframe"),
    )


def extract_screen_fingerprint(step: dict, file_name: str) -> str | None:
    action = extract_main_action(step)
    element = extract_element_target(action)

    return first_non_empty(
        element.get("contexto_tela"),
        step.get("contexto_tela"),
        step.get("tela"),
        step.get("modulo"),
        file_name.replace(".json", "").replace("_", " "),
    )


def is_good_enough(skill: KnownSkill) -> bool:
    if skill.semantic_target == "alvo não identificado":
        return False

    # ignora conclusões vazias
    bad_targets = {
        "confirmation",
        "navigation",
        "action",
        "deletion",
        "form_fill",
    }
    if skill.semantic_target.strip().lower() in bad_targets:
        return False

    if len(skill.semantic_target.strip()) < 3:
        return False

    return True


def write_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    if not INPUT_DIR.exists():
        print(f"Pasta não encontrada: {INPUT_DIR}")
        sys.exit(1)

    if OUTPUT_SKILLS.exists():
        OUTPUT_SKILLS.unlink()
    if OUTPUT_REVIEW.exists():
        OUTPUT_REVIEW.unlink()

    imported = 0
    skipped = 0

    for file in INPUT_DIR.glob("*.json"):
        try:
            payload = load_json(file)
        except Exception as e:
            write_jsonl(
                OUTPUT_REVIEW,
                {
                    "file": file.name,
                    "reason": f"json_error: {e}",
                },
            )
            skipped += 1
            continue

        for idx, step in enumerate(iter_steps(payload), start=1):
            skill = KnownSkill(
                skill_id=f"skill_{uuid4().hex[:12]}",
                semantic_target=extract_semantic_target(step),
                goal_type=infer_goal_type(step, file.name),
                screen_fingerprint=extract_screen_fingerprint(step, file.name),
                preferred_selector=extract_selector(step),
                preferred_iframe=extract_iframe(step),
                confidence=0.70,
                source="legacy_json",
            )

            if is_good_enough(skill):
                write_jsonl(OUTPUT_SKILLS, skill.model_dump())
                imported += 1
            else:
                write_jsonl(
                    OUTPUT_REVIEW,
                    {
                        "file": file.name,
                        "step_index": idx,
                        "reason": "low_quality_skill",
                        "semantic_target": skill.semantic_target,
                        "goal_type": skill.goal_type,
                        "raw_step_excerpt": json.dumps(step, ensure_ascii=False)[:500],
                    },
                )
                skipped += 1

    print("=" * 80)
    print(f"Skills importadas : {imported}")
    print(f"Passos ignorados  : {skipped}")
    print(f"Arquivo skills    : {OUTPUT_SKILLS}")
    print(f"Arquivo revisão   : {OUTPUT_REVIEW}")


if __name__ == "__main__":
    main()