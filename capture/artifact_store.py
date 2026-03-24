from __future__ import annotations

from pathlib import Path


class ArtifactStore:
    def __init__(self, root: str = "runtime_artifacts/capture"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def ensure_dir(self, name: str) -> Path:
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path