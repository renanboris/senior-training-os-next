from __future__ import annotations

from contracts.resolved_target import ResolvedTarget
from vision.strategies.base import ResolutionContext, Strategy
from vision.trace import DecisionTrace


class TargetResolver:
    def __init__(self, strategies: list[Strategy]):
        self.strategies = strategies

    async def resolve(self, page, ctx: ResolutionContext) -> tuple[ResolvedTarget, DecisionTrace]:
        trace = DecisionTrace()

        for strategy in self.strategies:
            trace.add(f"Tentando strategy: {strategy.name}")
            result = await strategy.try_resolve(page, ctx)
            if result:
                trace.add(
                    f"Strategy vencedora: {strategy.name} (confidence={result.resolution_confidence:.2f})"
                )
                return result, trace
            trace.add(f"Strategy falhou: {strategy.name}")

        raise RuntimeError(
            f"Nenhuma strategy conseguiu resolver o alvo para intent={ctx.intent.intent_id}"
        )