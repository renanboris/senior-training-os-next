from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class TimelineAudioItem(BaseModel):
    step_id: str
    text: str
    audio_file: str
    start_sec: float
    end_sec: float


class JobManifest(BaseModel):
    job_id: str
    training_id: str
    lesson_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    browser_video_path: Optional[str] = None
    output_mp4_path: Optional[str] = None
    output_srt_path: Optional[str] = None
    cut_start_sec: float = 0.0
    audio_timeline: list[TimelineAudioItem] = []


class JobManifestStore:
    def __init__(self, root: str = "runtime_artifacts/jobs"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, manifest: JobManifest) -> str:
        path = self.root / f"{manifest.job_id}.json"
        path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return str(path)

    def load(self, job_id: str) -> JobManifest:
        path = self.root / f"{job_id}.json"
        return JobManifest.model_validate_json(path.read_text(encoding="utf-8"))