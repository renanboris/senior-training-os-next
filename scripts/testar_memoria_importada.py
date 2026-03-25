from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.known_skill import KnownSkill
from contracts.intent_action import IntentAction, ExpectedEffect
from contracts.screen_state import ScreenState
from cil.skill_memory import SkillMemory


def load_skills(path: Path) -> list[KnownSkill]:
    skills = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        skills.append(KnownSkill(**json.loads(line)))
    return skills


def test_query(memory: SkillMemory, objective: str, goal_type: str, semantic_target: str, fingerprint: str | None = None):
    state = ScreenState(
        url="/ged",
        title="GED",
        fingerprint=fingerprint,
        primary_area="ged",
    )

    intent = IntentAction(
        intent_id="intent_test",
        goal_type=goal_type,
        semantic_target=semantic_target,
        expected_effect=ExpectedEffect(
            effect_type="screen_change",
            description="Teste de consulta à memória",
        ),
    )

    matches = memory.retrieve(state, intent)

    print("=" * 80)
    print(f"OBJETIVO         : {objective}")
    print(f"QUERY goal_type  : {goal_type}")
    print(f"QUERY target     : {semantic_target}")
    print(f"FINGERPRINT      : {fingerprint}")
    print(f"MATCHES          : {len(matches)}")

    for idx, item in enumerate(matches[:10], start=1):
        print(f"[{idx}] target={item.semantic_target} | goal={item.goal_type} | conf={item.confidence} | fp={item.screen_fingerprint}")


def main():
    path = ROOT / "data" / "legacy" / "imported_skills.jsonl"
    if not path.exists():
        print("Arquivo não encontrado:", path)
        return

    skills = load_skills(path)
    memory = SkillMemory()
    memory.seed(skills)

    print(f"Skills carregadas: {len(skills)}")

    # Testes simples
    test_query(
        memory,
        objective="Excluir uma pasta do GED",
        goal_type="delete",
        semantic_target="Excluir",
        fingerprint=None,
    )

    test_query(
        memory,
        objective="Pesquisar Senior Flow",
        goal_type="search",
        semantic_target="Senior Flow",
        fingerprint=None,
    )

    test_query(
        memory,
        objective="Abrir pasta Logistica",
        goal_type="open",
        semantic_target="Logistica",
        fingerprint=None,
    )


if __name__ == "__main__":
    main()