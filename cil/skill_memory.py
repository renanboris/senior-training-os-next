from __future__ import annotations

from contracts.execution_result import ExecutionResult
from contracts.intent_action import IntentAction
from contracts.known_skill import KnownSkill
from contracts.screen_state import ScreenState


class SkillMemory:
    def __init__(self):
        self._items: list[KnownSkill] = []

    def seed(self, skills: list[KnownSkill]) -> None:
        self._items.extend(skills)

    def retrieve(self, state: ScreenState, intent: IntentAction) -> list[KnownSkill]:
        matches: list[KnownSkill] = []
        for item in self._items:
            if item.goal_type != intent.goal_type:
                continue
            left = item.semantic_target.lower()
            right = intent.semantic_target.lower()
            if left not in right and right not in left:
                continue
            if item.screen_fingerprint and state.fingerprint and item.screen_fingerprint != state.fingerprint:
                continue
            matches.append(item)
        return sorted(matches, key=lambda x: x.confidence, reverse=True)

    def learn(self, intent: IntentAction, result: ExecutionResult, preferred_selector: str | None = None) -> KnownSkill | None:
        if result.status != 'success':
            return None
        skill = KnownSkill(
            skill_id=f"skill_{intent.intent_id}",
            semantic_target=intent.semantic_target,
            goal_type=intent.goal_type,
            preferred_selector=preferred_selector,
            confidence=min((result.telemetry.resolution_confidence or 0.5) + 0.1, 0.99),
            source='runtime_learning',
        )
        self._items.append(skill)
        return skill