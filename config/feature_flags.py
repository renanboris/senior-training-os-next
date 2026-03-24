from __future__ import annotations

import os
from dataclasses import dataclass


def _flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class FeatureFlags:
    use_new_capture_pipeline: bool = _flag("USE_NEW_CAPTURE_PIPELINE", False)
    use_strategy_vision: bool = _flag("USE_STRATEGY_VISION", False)
    use_split_runtime: bool = _flag("USE_SPLIT_RUNTIME", False)
    use_cil_shadow_mode: bool = _flag("USE_CIL_SHADOW_MODE", True)
    use_cil_low_risk_prod: bool = _flag("USE_CIL_LOW_RISK_PROD", False)
    use_cil_medium_risk_prod: bool = _flag("USE_CIL_MEDIUM_RISK_PROD", False)
    use_cil_high_risk_prod: bool = _flag("USE_CIL_HIGH_RISK_PROD", False)