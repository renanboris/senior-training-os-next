from __future__ import annotations

from dataclasses import asdict
from typing import Any

from cil.interpreter import IntentInterpreter
from cil.observer import ScreenObserver
from cil.planner import Planner
from cil.policy import PolicyEngine
from orchestration.comparison_report import ComparisonReportBuilder
from orchestration.evaluation_logger import EvaluationLogger
from orchestration.legacy_bridge import LegacyBridge
from vision.resolver import TargetResolver
from vision.strategies.base import ResolutionContext


class ShadowModeRunner:
    def __init__(
        self,
        resolver: TargetResolver,
        executor,
        skill_memory,
        legacy_bridge: LegacyBridge | None = None,
        logger: EvaluationLogger | None = None,
    ):
        self.observer = ScreenObserver()
        self.interpreter = IntentInterpreter()
        self.planner = Planner()
        self.policy = PolicyEngine()
        self.resolver = resolver
        self.executor = executor
        self.skill_memory = skill_memory
        self.legacy_bridge = legacy_bridge or LegacyBridge()
        self.logger = logger or EvaluationLogger()
        self.report_builder = ComparisonReportBuilder()

    async def run_from_observed_action(
        self,
        page,
        observed_action,
        lesson_name: str,
        step_index: int,
        total_steps: int,
    ) -> dict[str, Any]:
        screen_state = await self.observer.observe(page)
        inferred_intent = self.interpreter.interpret(observed_action, screen_state)
        risk = self.policy.evaluate(inferred_intent)
        known_skills = self.skill_memory.retrieve(screen_state, inferred_intent)

        resolution_context = ResolutionContext(
            intent=inferred_intent,
            screen_state=screen_state,
            known_skills=[skill.model_dump() for skill in known_skills],
        )

        resolved_target, trace = await self.resolver.resolve(page, resolution_context)

        execution_result = await self.executor.execute(
            page=page,
            intent=inferred_intent,
            target=resolved_target,
            before_snapshot=observed_action.screen_before,
            step_index=step_index,
            total_steps=total_steps,
            lesson_name=lesson_name,
            subtitle_text=inferred_intent.pedagogical_value,
        )

        legacy_step = self.legacy_bridge.get_step_for_event(observed_action.event_id, index=step_index - 1)
        comparison = self.report_builder.compare(
            legacy_step=legacy_step,
            inferred_intent=inferred_intent,
            execution_result=execution_result,
            resolved_target=resolved_target,
        )

        record = {
            "event_id": observed_action.event_id,
            "intent": inferred_intent.model_dump(),
            "risk": risk.model_dump(),
            "resolved_target": resolved_target.model_dump(),
            "execution_result": execution_result.model_dump(),
            "trace": trace.steps,
            "comparison": asdict(comparison),
        }
        path = self.logger.append(record)

        return {
            "saved_to": path,
            "record": record,
        }

    async def run_from_objective(
        self,
        page,
        objective: str,
        history: list,
        lesson_name: str,
        step_index: int,
        total_steps: int,
    ) -> dict[str, Any]:
        screen_state = await self.observer.observe(page)
        known_skills = self.skill_memory.retrieve(
            screen_state,
            self.planner.next_action(objective, screen_state, history, []),
        )
        planned_intent = self.planner.next_action(objective, screen_state, history, known_skills)
        risk = self.policy.evaluate(planned_intent)

        resolution_context = ResolutionContext(
            intent=planned_intent,
            screen_state=screen_state,
            known_skills=[skill.model_dump() for skill in known_skills],
        )

        resolved_target, trace = await self.resolver.resolve(page, resolution_context)

        execution_result = await self.executor.execute(
            page=page,
            intent=planned_intent,
            target=resolved_target,
            before_snapshot=screen_state,
            step_index=step_index,
            total_steps=total_steps,
            lesson_name=lesson_name,
            subtitle_text=planned_intent.pedagogical_value,
        )

        record = {
            "objective": objective,
            "intent": planned_intent.model_dump(),
            "risk": risk.model_dump(),
            "resolved_target": resolved_target.model_dump(),
            "execution_result": execution_result.model_dump(),
            "trace": trace.steps,
        }
        path = self.logger.append(record)

        return {
            "saved_to": path,
            "record": record,
        }