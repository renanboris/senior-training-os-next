from __future__ import annotations

from contracts.intent_action import IntentAction
from contracts.resolved_target import ResolvedTarget


class ResolutionValidator:
    def requires_hard_validation(self, intent: IntentAction, target: ResolvedTarget) -> bool:
        if intent.goal_type in {"save", "delete", "confirm"}:
            return True
        if target.strategy_used in {"vision", "coordinates"}:
            return True
        return target.needs_extra_validation