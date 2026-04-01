"""OfflinePipeline — processa arquivos shadow.jsonl sem browser ativo.

CLI:
    python -m orchestration.offline_pipeline <arquivo.jsonl>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypedDict

from capture.shadow_ingestion import (
    event_to_skill,
    filter_useful_events,
    load_jsonl,
)
from contracts.known_skill import KnownSkill


class PipelineInputError(ValueError):
    """Arquivo de entrada não encontrado ou inválido."""


class ImportReport(TypedDict):
    total_events: int
    useful_events: int
    skills_generated: int
    skills_discarded: int


class OfflinePipeline:
    def __init__(self, skill_memory, min_confidence: float = 0.5) -> None:
        """
        Args:
            skill_memory: instância de SkillMemory para persistir skills geradas.
            min_confidence: threshold mínimo de confiança para aceitar uma skill.
        """
        self._skill_memory = skill_memory
        self._min_confidence = min_confidence

    def run(self, jsonl_path: Path) -> tuple[list[KnownSkill], ImportReport]:
        """Processa um arquivo shadow.jsonl e retorna skills + relatório.

        Raises:
            PipelineInputError: se o arquivo não existir.
        """
        if not jsonl_path.exists():
            raise PipelineInputError(f"Arquivo não encontrado: {jsonl_path}")

        events = load_jsonl(jsonl_path)
        total_events = len(events)

        useful = filter_useful_events(events)
        useful_count = len(useful)

        accepted: list[KnownSkill] = []
        discarded = 0

        for event in useful:
            raw = event_to_skill(event)
            if raw["confidence"] < self._min_confidence:
                discarded += 1
                continue
            try:
                skill = KnownSkill(**raw)
                accepted.append(skill)
            except Exception:
                discarded += 1

        if accepted:
            self._skill_memory.seed(accepted)
            # Persiste no backend se disponível
            if self._skill_memory._backend is not None:
                self._skill_memory._backend.save(self._skill_memory._items)

        report: ImportReport = {
            "total_events": total_events,
            "useful_events": useful_count,
            "skills_generated": len(accepted),
            "skills_discarded": discarded,
        }
        return accepted, report


def _main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m orchestration.offline_pipeline <arquivo.jsonl>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])

    from cil.skill_memory import SkillMemory
    memory = SkillMemory()
    pipeline = OfflinePipeline(skill_memory=memory)

    try:
        skills, report = pipeline.run(path)
    except PipelineInputError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    _main()
