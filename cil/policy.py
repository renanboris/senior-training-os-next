from __future__ import annotations

from pydantic import BaseModel

from contracts.intent_action import IntentAction


class RiskDecision(BaseModel):
    risk_level: str
    needs_confirmation: bool = False
    allow_coordinate_fallback: bool = True
    require_post_validation: bool = True


class PolicyEngine:
    def evaluate(self, intent: IntentAction) -> RiskDecision:
        if intent.goal_type in {'save', 'delete', 'confirm'}:
            return RiskDecision(
                risk_level='high',
                needs_confirmation=True,
                allow_coordinate_fallback=False,
                require_post_validation=True,
            )
        if intent.goal_type in {'upload', 'download'}:
            return RiskDecision(
                risk_level='medium',
                needs_confirmation=False,
                allow_coordinate_fallback=True,
                require_post_validation=True,
            )
        return RiskDecision(
            risk_level='low',
            needs_confirmation=False,
            allow_coordinate_fallback=True,
            require_post_validation=False,
        )