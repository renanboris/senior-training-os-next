from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Importa o parser diretamente para testar sem executar o main
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.run_tutorial import _build_parser


def _parse(args: list[str]):
    return _build_parser().parse_args(args)


def test_cli_defaults():
    args = _parse(["shadow.jsonl"])
    assert args.shadow_file == Path("shadow.jsonl")
    assert not args.replay
    assert not args.guide
    assert not args.record_only
    assert not args.headless
    assert args.min_step_duration == 1.5
    assert args.speed_factor == 1.0
    assert args.max_events == 0


def test_cli_headless_flag():
    args = _parse(["shadow.jsonl", "--headless"])
    assert args.headless is True


def test_cli_guide_mode():
    args = _parse(["shadow.jsonl", "--guide"])
    assert args.guide is True
    assert not args.replay
    assert not args.record_only


def test_cli_record_only_mode():
    args = _parse(["shadow.jsonl", "--record-only"])
    assert args.record_only is True
    assert not args.guide
    assert not args.replay


def test_cli_replay_mode():
    args = _parse(["shadow.jsonl", "--replay"])
    assert args.replay is True


def test_cli_mutually_exclusive_modes():
    with pytest.raises(SystemExit) as exc_info:
        _parse(["shadow.jsonl", "--replay", "--guide"])
    assert exc_info.value.code == 2


def test_cli_max_events():
    args = _parse(["shadow.jsonl", "--max-events", "3"])
    assert args.max_events == 3


def test_cli_speed_factor():
    args = _parse(["shadow.jsonl", "--speed-factor", "0.5"])
    assert args.speed_factor == 0.5


def test_cli_min_step_duration():
    args = _parse(["shadow.jsonl", "--min-step-duration", "2.5"])
    assert args.min_step_duration == 2.5
