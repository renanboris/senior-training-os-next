from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from contracts.intent_action import IntentAction
from contracts.resolved_target import ResolvedTarget
from contracts.screen_state import ScreenState


@dataclass
class ResolutionContext:
    intent: IntentAction
    screen_state: ScreenState
    known_skills: list[dict[str, Any]] = field(default_factory=list)


class Strategy:
    name: str = "base"

    async def try_resolve(self, page, ctx: ResolutionContext) -> Optional[ResolvedTarget]:
        raise NotImplementedError