"""Script de teste/validação de shadow exports v2.

Delega toda a lógica de transformação para capture.shadow_ingestion.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from capture.shadow_ingestion import (
    event_to_skill,
    filter_useful_events,
    load_jsonl,
    write_skills,
)


def _compact(text: str | None) -> str:
    return " ".join((text or "").split()).strip()


def print_summary(events: list[dict]) -> None:
    print("=" * 80)
    print(f"Eventos úteis: {len(events)}")
    print("Ações semânticas brutas:")
    for name, count in Counter(e.get("semantic_action", "unknown") for e in events).most_common():
        print(f"  - {name}: {count}")
    print("Principais alvos:")
    for name, count in Counter(
        _compact(e.get("business_target")) or _compact(e.get("elemento_alvo", {}).get("label_curto")) or "sem alvo"
        for e in events
    ).most_common(10):
        print(f"  - {name}: {count}")
    print("=" * 80)


def build_dynamic_queries(skills: list[dict]) -> list[tuple[str, str]]:
    candidates = [
        ("open", "Financeiro"),
        ("open", "Contas a receber01.pdf"),
        ("open", "Coletar assinaturas"),
        ("fill", "E-mail"),
        ("fill", "renan.kirsch@senior.com.br"),
        ("fill", "Renan"),
        ("select", "Analisar e assinar"),
        ("confirm", "Sim"),
    ]
    available = {(s["goal_type"].lower(), s["semantic_target"].lower()) for s in skills}
    preferred = [(g, t) for g, t in candidates if (g.lower(), t.lower()) in available]
    if preferred:
        return preferred
    seen: set = set()
    fallback = []
    for s in skills:
        key = (s["goal_type"], s["semantic_target"])
        if key not in seen:
            seen.add(key)
            fallback.append(key)
        if len(fallback) >= 6:
            break
    return fallback


def infer_state_from_skills(skills: list[dict]):
    from contracts.screen_state import ScreenState
    fps = [s["screen_fingerprint"] for s in skills if s["screen_fingerprint"]]
    chosen = fps[0] if fps else "GED | X Platform"
    return ScreenState(url="/ged", title=chosen, fingerprint=chosen, primary_area="ged")


def try_project_integration(skills: list[dict]) -> None:
    try:
        from contracts.known_skill import KnownSkill
        from cil.skill_memory import SkillMemory
    except Exception as e:
        print(f"Integração indisponível: {e}")
        return

    typed_skills = [KnownSkill(**s) for s in skills]
    memory = SkillMemory()
    memory.seed(typed_skills)
    print(f"Integração com SkillMemory OK. Skills semeadas: {len(typed_skills)}")

    state = infer_state_from_skills(skills)
    queries = build_dynamic_queries(skills)

    class TmpIntent:
        def __init__(self, goal_type, semantic_target):
            self.goal_type = goal_type
            self.semantic_target = semantic_target

    for goal_type, semantic_target in queries:
        matches = memory.retrieve(state, TmpIntent(goal_type, semantic_target))
        print(f"Consulta -> {goal_type}/{semantic_target}: {len(matches)} matches")
        for idx, item in enumerate(matches[:3], 1):
            print(f"  [{idx}] {item.semantic_target} | fp={item.screen_fingerprint}")

    try:
        from cil.planner import Planner
        planned = Planner().next_action(
            "Enviar um arquivo para assinatura no GED", state, [], typed_skills
        )
        print(f"Planner: {planned.goal_type} / {planned.semantic_target} (conf={planned.semantic_confidence})")
    except Exception as e:
        print(f"Planner indisponível: {e}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/test_dual_output_shadow_v2.py shadow_exports/ARQUIVO_shadow.jsonl")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Arquivo não encontrado: {input_path}")
        sys.exit(1)

    events = load_jsonl(input_path)
    useful_events = filter_useful_events(events)
    print_summary(useful_events)

    skills = [event_to_skill(e) for e in useful_events]
    out_path = ROOT / "data" / "dual_output" / "imported_skills_from_shadow_v2.jsonl"
    write_skills(skills, out_path)

    print(f"Skills geradas: {len(skills)}")
    print(f"Arquivo skills: {out_path}")
    print("\nExemplos:")
    for item in skills[:5]:
        print(json.dumps(item, ensure_ascii=False, indent=2))

    try_project_integration(skills)


if __name__ == "__main__":
    main()
