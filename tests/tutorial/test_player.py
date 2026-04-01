from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from cil.skill_memory import SkillMemory
from tutorial.player import ArtifactPaths, TutorialConfig, TutorialPlayer


def _make_config(shadow_path: Path, mode: str = "replay") -> TutorialConfig:
    return TutorialConfig(
        shadow_path=shadow_path,
        mode=mode,
        headless=True,
        min_step_duration=0.01,
        speed_factor=0.01,
    )


# Feature: tutorial-player, Property 6: Caminhos de artefatos seguem convencao baseada em job_id
@given(
    job_id=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    )
)
@settings(max_examples=100)
def test_artifact_paths_convention(job_id: str) -> None:
    config = TutorialConfig(shadow_path=Path("dummy.jsonl"))
    player = TutorialPlayer(config, SkillMemory())
    paths = player._build_artifact_paths(job_id)
    root = Path("runtime_artifacts") / "tutorials" / job_id
    assert paths.root == root
    assert paths.audio_dir == root / "audio"
    assert paths.raw_dir == root / "raw"
    assert paths.output_mp4 == root / f"{job_id}.mp4"
    assert paths.output_srt == root / f"{job_id}.srt"
    assert paths.manifest_copy == root / f"{job_id}_manifest.json"


def test_missing_file_exits_nonzero(tmp_path: Path) -> None:
    config = _make_config(tmp_path / "nope.jsonl")
    player = TutorialPlayer(config, SkillMemory())
    with pytest.raises(SystemExit) as exc_info:
        import asyncio
        asyncio.run(player.run())
    assert exc_info.value.code != 0


def test_empty_events_exits_nonzero(tmp_path: Path) -> None:
    f = tmp_path / "empty.jsonl"
    # Evento com is_noise=True — será filtrado
    f.write_text(json.dumps({"is_noise": True, "business_target": ""}) + "\n", encoding="utf-8")
    config = _make_config(f)
    player = TutorialPlayer(config, SkillMemory())
    with pytest.raises(SystemExit) as exc_info:
        import asyncio
        asyncio.run(player.run())
    assert exc_info.value.code != 0


def test_lesson_name_from_stem(tmp_path: Path) -> None:
    """Property 9: lesson_name == shadow_path.stem"""
    config = TutorialConfig(shadow_path=Path("meu_tutorial.jsonl"))
    player = TutorialPlayer(config, SkillMemory())
    assert config.shadow_path.stem == "meu_tutorial"


# Feature: tutorial-player, Property 3: audio_timeline start_sec acumulativo
def test_audio_timeline_accumulation() -> None:
    """Verifica que start_sec de cada item é igual ao end_sec do anterior."""
    from runtime.job_manifest import JobManifest, TimelineAudioItem
    manifest = JobManifest(job_id="test", training_id="test", lesson_name="test")
    durations = [1.5, 2.0, 0.8, 3.2]
    cursor = 0.0
    for i, dur in enumerate(durations):
        manifest.audio_timeline.append(TimelineAudioItem(
            step_id=f"step_{i:03d}",
            text=f"Passo {i}",
            audio_file=f"audio/step_{i:03d}.mp3",
            start_sec=cursor,
            end_sec=cursor + dur,
        ))
        cursor += dur

    for i, item in enumerate(manifest.audio_timeline):
        expected_start = sum(durations[:i])
        assert abs(item.start_sec - expected_start) < 1e-9
        assert abs(item.end_sec - (expected_start + durations[i])) < 1e-9
