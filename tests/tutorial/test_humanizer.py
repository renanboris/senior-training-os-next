from __future__ import annotations

import math
import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tutorial.humanizer import HumanizedDelay


def test_calculate_uses_audio_duration_when_larger():
    hd = HumanizedDelay(min_step_duration=1.0, speed_factor=1.0, rng=random.Random(42))
    delay = hd.calculate(5.0)
    # base = max(5.0, 1.0) = 5.0; jitter in [0.2, 0.8]; delay in [5.2, 5.8]
    assert 5.2 <= delay <= 5.8


def test_calculate_uses_min_step_when_larger():
    hd = HumanizedDelay(min_step_duration=3.0, speed_factor=1.0, rng=random.Random(42))
    delay = hd.calculate(0.5)
    # base = max(0.5, 3.0) = 3.0; delay in [3.2, 3.8]
    assert 3.2 <= delay <= 3.8


def test_speed_factor_scales_delay():
    hd = HumanizedDelay(min_step_duration=1.0, speed_factor=2.0, rng=random.Random(42))
    delay = hd.calculate(0.0)
    # base = 1.0; delay in [1.2*2, 1.8*2] = [2.4, 3.6]
    assert 2.4 <= delay <= 3.6


# Feature: tutorial-player, Property 2: Humanized_Delay satisfaz bounds matematicos
@given(
    audio_duration=st.floats(min_value=0.0, max_value=30.0, allow_nan=False, allow_infinity=False),
    min_step=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    speed=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_humanized_delay_bounds(audio_duration: float, min_step: float, speed: float) -> None:
    hd = HumanizedDelay(min_step_duration=min_step, speed_factor=speed)
    delay = hd.calculate(audio_duration)
    base = max(audio_duration, min_step)
    lower = (base + 0.2) * speed
    upper = (base + 0.8) * speed
    assert lower <= delay <= upper + 1e-9  # tolerância de ponto flutuante
