from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from contracts.execution_result import ExecutionResult
from contracts.intent_action import IntentAction
from contracts.known_skill import KnownSkill
from contracts.screen_state import ScreenState
from cil.text_utils import SimilarityMatcher, TextNormalizer

logger = logging.getLogger(__name__)


@runtime_checkable
class SkillBackend(Protocol):
    """Interface de persistência para SkillMemory."""

    def load(self) -> list[KnownSkill]: ...
    def save(self, skills: list[KnownSkill]) -> None: ...


class JsonlSkillBackend:
    """Backend de persistência baseado em arquivo JSONL."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[KnownSkill]:
        if not self.path.exists():
            return []
        skills: list[KnownSkill] = []
        for lineno, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = line.strip()
            if not line:
                continue
            try:
                skills.append(KnownSkill.model_validate(json.loads(line)))
            except Exception as exc:
                logger.warning(
                    "JsonlSkillBackend: linha %d ignorada (malformada): %s", lineno, exc
                )
        return skills

    def save(self, skills: list[KnownSkill]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for skill in skills:
                f.write(json.dumps(skill.model_dump(), ensure_ascii=True) + "\n")


class SkillMemory:
    def __init__(
        self,
        backend: Optional[SkillBackend] = None,
        similarity_threshold: float = 0.7,
    ) -> None:
        self._backend = backend
        self._threshold = similarity_threshold
        self._matcher = SimilarityMatcher()
        self._normalizer = TextNormalizer()
        self._items: list[KnownSkill] = []

        if backend is not None:
            self._items = list(backend.load())

    def seed(self, skills: list[KnownSkill]) -> None:
        self._items.extend(skills)

    def retrieve(self, state: ScreenState, intent: IntentAction) -> list[KnownSkill]:
        matches: list[KnownSkill] = []
        for item in self._items:
            if item.goal_type != intent.goal_type:
                continue
            score = self._matcher.score(item.semantic_target, intent.semantic_target)
            if score < self._threshold:
                continue
            if (
                item.screen_fingerprint
                and state.fingerprint
                and item.screen_fingerprint != state.fingerprint
            ):
                continue
            matches.append(item)
        return sorted(matches, key=lambda x: x.confidence, reverse=True)

    def learn(
        self,
        intent: IntentAction,
        result: ExecutionResult,
        preferred_selector: Optional[str] = None,
    ) -> Optional[KnownSkill]:
        if result.status != "success":
            return None

        # Deduplicação: não aprende se já existe skill idêntica
        for existing in self._items:
            if (
                existing.goal_type == intent.goal_type
                and self._matcher.score(existing.semantic_target, intent.semantic_target) >= 0.95
            ):
                return None

        skill = KnownSkill(
            skill_id=f"skill_{intent.intent_id}",
            semantic_target=intent.semantic_target,
            goal_type=intent.goal_type,
            preferred_selector=preferred_selector,
            confidence=min(
                (result.telemetry.resolution_confidence or 0.5) + 0.1, 0.99
            ),
            source="runtime_learning",
        )
        self._items.append(skill)

        if self._backend is not None:
            self._backend.save(self._items)

        return skill
