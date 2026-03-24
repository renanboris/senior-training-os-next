from cil.skill_memory import SkillMemory
from contracts.intent_action import ExpectedEffect, IntentAction
from contracts.known_skill import KnownSkill
from contracts.screen_state import ScreenState


def test_skill_memory_retrieves_matching_skill():
    memory = SkillMemory()
    memory.seed([
        KnownSkill(
            skill_id="skill_001",
            semantic_target="Pesquisar documento",
            goal_type="search",
            screen_fingerprint="ged_fingerprint",
            confidence=0.91,
        )
    ])

    state = ScreenState(fingerprint="ged_fingerprint")
    intent = IntentAction(
        intent_id="int_001",
        goal_type="search",
        semantic_target="Pesquisar documento",
        expected_effect=ExpectedEffect(effect_type="grid_refresh", description="Atualiza a grade"),
    )

    matches = memory.retrieve(state, intent)

    assert len(matches) == 1
    assert matches[0].skill_id == "skill_001"