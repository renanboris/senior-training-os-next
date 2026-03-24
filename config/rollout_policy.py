from __future__ import annotations

from dataclasses import dataclass

from config.feature_flags import FeatureFlags
from contracts.intent_action import IntentAction


@dataclass
class RolloutDecision:
    mode: str
    reason: str


class RolloutPolicy:
    def __init__(self, flags: FeatureFlags):
        self.flags = flags

    def decide(self, intent: IntentAction) -> RolloutDecision:
        if not self.flags.use_cil_shadow_mode:
            return RolloutDecision(mode="legacy_only", reason="Shadow mode desativado.")

        if intent.goal_type in {"save", "delete", "confirm"}:
            if self.flags.use_cil_high_risk_prod:
                return RolloutDecision(mode="cil_prod", reason="CIL liberado para alto risco.")
            return RolloutDecision(mode="shadow_only", reason="Ação de alto risco permanece em observação.")

        if intent.goal_type in {"upload", "download"}:
            if self.flags.use_cil_medium_risk_prod:
                return RolloutDecision(mode="cil_prod", reason="CIL liberado para médio risco.")
            return RolloutDecision(mode="shadow_only", reason="Ação de médio risco permanece em observação.")

        if self.flags.use_cil_low_risk_prod:
            return RolloutDecision(mode="cil_prod", reason="CIL liberado para baixo risco.")

        return RolloutDecision(mode="shadow_only", reason="Ação de baixo risco ainda em shadow mode.")