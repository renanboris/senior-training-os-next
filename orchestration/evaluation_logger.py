from __future__ import annotations

import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


class EvaluationLogger:
    def __init__(self, root: str = "runtime_artifacts/evaluations") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> str:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.root / f"shadow_eval_{day}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")  # bug corrigido: \n
        return str(path)

    def _path_for_date(self, date: str | None) -> Path:
        day = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.root / f"shadow_eval_{day}.jsonl"

    def aggregate(self, date: str | None = None) -> dict:
        """Agrega métricas do arquivo JSONL do dia especificado.

        Retorna dict com campos zerados se o arquivo não existir.
        """
        path = self._path_for_date(date)
        empty = {
            "total_executions": 0,
            "success_rate": 0.0,
            "effect_verified_rate": 0.0,
            "strategy_distribution": {},
            "avg_duration_ms": 0.0,
            "p95_duration_ms": 0.0,
        }

        if not path.exists():
            return empty

        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if not records:
            return empty

        total = len(records)
        successes = sum(
            1 for r in records
            if r.get("execution_result", {}).get("status") == "success"
        )
        verified = sum(
            1 for r in records
            if r.get("execution_result", {}).get("effect_verified", False)
        )

        strategy_dist: dict[str, int] = {}
        durations: list[float] = []
        for r in records:
            strategy = (r.get("resolved_target") or {}).get("strategy_used")
            if strategy:
                strategy_dist[strategy] = strategy_dist.get(strategy, 0) + 1
            dur = r.get("execution_result", {}).get("duration_ms")
            if dur is not None:
                durations.append(float(dur))

        avg_dur = statistics.mean(durations) if durations else 0.0
        p95_dur = 0.0
        if durations:
            sorted_dur = sorted(durations)
            idx = max(0, int(len(sorted_dur) * 0.95) - 1)
            p95_dur = sorted_dur[idx]

        return {
            "total_executions": total,
            "success_rate": round(successes / total, 4),
            "effect_verified_rate": round(verified / total, 4),
            "strategy_distribution": strategy_dist,
            "avg_duration_ms": round(avg_dur, 2),
            "p95_duration_ms": round(p95_dur, 2),
        }

    def export_csv(self, date: str | None, out_path: Path) -> None:
        """Exporta métricas agregadas em formato CSV."""
        metrics = self.aggregate(date)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            for key, value in metrics.items():
                if key == "strategy_distribution":
                    for strategy, count in value.items():
                        writer.writerow([f"strategy_{strategy}", count])
                else:
                    writer.writerow([key, value])
