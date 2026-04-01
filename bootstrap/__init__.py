"""Bootstrap — factory de pipeline para o sistema de automação semântica.

Uso:
    from bootstrap import create_pipeline
    pipeline = create_pipeline()
    skill_memory = pipeline["skill_memory"]
    shadow_runner = pipeline["shadow_runner"]
"""
from __future__ import annotations

from typing import Any


def create_pipeline(flags=None) -> dict[str, Any]:
    """Instancia e retorna o pipeline completo com configuração padrão.

    Args:
        flags: instância de FeatureFlags. Se None, usa valores padrão de env vars.

    Returns:
        dict com chaves: skill_memory, resolver, interpreter, planner,
        effect_verifier, evaluation_logger, shadow_runner.
    """
    from config.feature_flags import FeatureFlags
    from cil.skill_memory import SkillMemory
    from cil.interpreter import IntentInterpreter
    from cil.planner import Planner
    from runtime.effect_verifier import EffectVerifier
    from orchestration.evaluation_logger import EvaluationLogger
    from orchestration.shadow_mode_runner import ShadowModeRunner
    from vision.resolver import TargetResolver
    from vision.strategies.cache_strategy import CacheStrategy
    from vision.strategies.active_element_strategy import ActiveElementStrategy
    from vision.strategies.dom_strategy import DomStrategy
    from vision.strategies.frame_strategy import FrameStrategy
    from vision.strategies.coordinate_strategy import CoordinateStrategy

    if flags is None:
        flags = FeatureFlags()

    skill_memory = SkillMemory()

    # Monta chain de strategies
    strategies = [
        CacheStrategy(cache_lookup=lambda target: None),
        ActiveElementStrategy(),
        DomStrategy(),
        FrameStrategy(),
    ]

    if flags.use_strategy_vision:
        from vision.strategies.vision_strategy import VisionStrategy
        from cil.llm_client import LLMClient
        strategies.append(VisionStrategy(llm_client=LLMClient()))

    strategies.append(CoordinateStrategy(coordinate_lookup=lambda target: None))

    resolver = TargetResolver(strategies=strategies)
    interpreter = IntentInterpreter(flags=flags)
    planner = Planner()
    effect_verifier = EffectVerifier()
    evaluation_logger = EvaluationLogger()

    shadow_runner = ShadowModeRunner(
        resolver=resolver,
        executor=None,  # injetado externamente quando necessário
        skill_memory=skill_memory,
        logger=evaluation_logger,
    )

    return {
        "skill_memory": skill_memory,
        "resolver": resolver,
        "interpreter": interpreter,
        "planner": planner,
        "effect_verifier": effect_verifier,
        "evaluation_logger": evaluation_logger,
        "shadow_runner": shadow_runner,
    }
