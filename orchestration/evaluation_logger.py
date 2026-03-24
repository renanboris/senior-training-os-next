from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json


class EvaluationLogger:
    def __init__(self, root: str = "runtime_artifacts/evaluations"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> str:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.root / f"shadow_eval_{day}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "")
        return str(path)