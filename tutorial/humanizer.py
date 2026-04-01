from __future__ import annotations

import asyncio
import random
from typing import Optional


class HumanizedDelay:
    """Calcula e aplica delays naturais entre Steps do Tutorial Player.

    O delay é calculado como:
        (max(audio_duration, min_step_duration) + jitter) * speed_factor
    onde jitter é um valor aleatório entre 0.2 e 0.8 segundos.
    """

    def __init__(
        self,
        min_step_duration: float = 1.5,
        speed_factor: float = 1.0,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.min_step_duration = min_step_duration
        self.speed_factor = speed_factor
        self._rng = rng or random.Random()

    def calculate(self, audio_duration: float) -> float:
        """Retorna o delay calculado em segundos."""
        base = max(audio_duration, self.min_step_duration)
        jitter = self._rng.uniform(0.2, 0.8)
        return (base + jitter) * self.speed_factor

    async def wait(self, audio_duration: float) -> None:
        """Calcula e aplica o delay via asyncio.sleep."""
        delay = self.calculate(audio_duration)
        await asyncio.sleep(delay)
