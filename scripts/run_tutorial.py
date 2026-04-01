"""Tutorial Player CLI.

Uso (Windows PowerShell):
    py scripts/run_tutorial.py shadow_exports/TESTE_DUAL_002_shadow.jsonl
    py scripts/run_tutorial.py shadow_exports/TESTE_DUAL_002_shadow.jsonl --guide
    py scripts/run_tutorial.py shadow_exports/TESTE_DUAL_002_shadow.jsonl --record-only
    py scripts/run_tutorial.py shadow_exports/TESTE_DUAL_002_shadow.jsonl --headless
    py scripts/run_tutorial.py shadow_exports/TESTE_DUAL_002_shadow.jsonl --max-events 5
    py scripts/run_tutorial.py shadow_exports/TESTE_DUAL_002_shadow.jsonl --speed-factor 0.5

Modos:
  --replay (padrao)  Navega, destaca, narra e executa as acoes reais.
  --guide            Navega e destaca elementos sem executar acoes.
  --record-only      Grava o video sem overlays visuais.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Carrega .env
_env_path = ROOT / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        _k = _k.strip()
        _v = _v.strip().strip('"').strip("'")
        if _k and _k not in os.environ:
            os.environ[_k] = _v


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_tutorial",
        description="Tutorial Player — reproduz sessoes capturadas como tutoriais humanizados.",
    )
    parser.add_argument(
        "shadow_file",
        type=Path,
        help="Caminho para o arquivo shadow.jsonl",
    )

    # Modos mutuamente exclusivos
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--replay",
        action="store_true",
        default=False,
        help="Navega, destaca e executa acoes reais (padrao)",
    )
    mode_group.add_argument(
        "--guide",
        action="store_true",
        default=False,
        help="Navega e destaca elementos sem executar acoes",
    )
    mode_group.add_argument(
        "--record-only",
        action="store_true",
        default=False,
        dest="record_only",
        help="Grava video sem overlays visuais",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Executa o browser sem interface grafica",
    )
    parser.add_argument(
        "--min-step-duration",
        type=float,
        default=1.5,
        metavar="FLOAT",
        help="Duracao minima de cada passo em segundos (padrao: 1.5)",
    )
    parser.add_argument(
        "--speed-factor",
        type=float,
        default=1.0,
        metavar="FLOAT",
        help="Fator de escala para todos os delays (padrao: 1.0)",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=0,
        metavar="INT",
        help="Limita o numero de eventos processados (0 = todos)",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Determina modo
    if args.record_only:
        mode = "record-only"
    elif args.guide:
        mode = "guide"
    else:
        mode = "replay"

    from cil.skill_memory import JsonlSkillBackend, SkillMemory
    from tutorial.player import TutorialConfig, TutorialPlayer

    skills_path = ROOT / "data" / "homolog" / "skills.jsonl"
    skills_path.parent.mkdir(parents=True, exist_ok=True)
    skill_memory = SkillMemory(backend=JsonlSkillBackend(skills_path))

    config = TutorialConfig(
        shadow_path=args.shadow_file,
        mode=mode,
        headless=args.headless,
        min_step_duration=args.min_step_duration,
        speed_factor=args.speed_factor,
        max_events=args.max_events,
    )

    asyncio.run(TutorialPlayer(config, skill_memory).run())


if __name__ == "__main__":
    main()
