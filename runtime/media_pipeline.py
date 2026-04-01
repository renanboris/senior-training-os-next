from __future__ import annotations

import os
import re
from pathlib import Path

import edge_tts

# Compatibilidade com MoviePy 1.x e 2.x
try:
    from moviepy.editor import AudioFileClip, CompositeAudioClip, VideoFileClip
    import moviepy.audio.fx.all as afx

    MOVIEPY_V2 = False
except Exception:
    from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip
    from moviepy.audio.fx.AudioLoop import AudioLoop

    MOVIEPY_V2 = True


class TTSService:
    def __init__(self, elevenlabs_async_client=None):
        self.elevenlabs_async_client = elevenlabs_async_client

    async def generate_audio(
        self,
        text: str,
        output_file: str,
        voice: str = "pt-BR-FranciscaNeural",
    ) -> str | None:
        if not text or not text.strip():
            return None

        spoken = re.sub(r"(?i)ecm_ged", "E C M gedi", text)
        spoken = re.sub(r"GED", "gedi", spoken)
        spoken = re.sub(r"(?i)senior", "Senior", spoken)

        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Tenta OpenAI TTS primeiro (mais confiavel); fallback para edge-tts
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                return await self._openai_tts(spoken, str(out), api_key)
            except Exception:
                pass  # cai para edge-tts

        # Fallback: edge-tts com voz Francisca pt-BR
        try:
            await edge_tts.Communicate(spoken, voice, rate="-12%").save(str(out))
            return str(out)
        except Exception as edge_err:
            raise RuntimeError(f"TTS falhou: {edge_err}")

    async def _openai_tts(self, text: str, output_file: str, api_key: str) -> str:
        """Gera audio via OpenAI TTS API — voz nova (feminina, proxima pt-BR)."""
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": "nova",
                    "response_format": "mp3",
                },
            )
            resp.raise_for_status()
            Path(output_file).write_bytes(resp.content)
        return output_file


def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class SubtitleWriter:
    def write_srt(self, timeline: list[dict], srt_path: str) -> None:
        output = Path(srt_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as f:
            for idx, item in enumerate(timeline, start=1):
                f.write(f"{idx}")

                f.write(
                    f"{format_srt_time(item['start_sec'])} --> {format_srt_time(item['end_sec'])}")
                f.write(f"{item['text']}")

class VideoRenderer:
    def _subclip(self, video, cut_start_sec: float):
        if MOVIEPY_V2:
            return video.subclipped(cut_start_sec)
        return video.subclip(cut_start_sec)

    def _set_audio(self, video, audio_clip):
        if MOVIEPY_V2:
            return video.with_audio(audio_clip)
        return video.set_audio(audio_clip)

    def _set_audio_start(self, audio_clip, start_sec: float):
        if MOVIEPY_V2:
            return audio_clip.with_start(start_sec)
        return audio_clip.set_start(start_sec)

    def _scale_volume(self, audio_clip, factor: float):
        if MOVIEPY_V2:
            return audio_clip.with_volume_scaled(factor)
        return audio_clip.volumex(factor)

    def _loop_audio(self, audio_clip, duration: float):
        if MOVIEPY_V2:
            return audio_clip.with_effects([AudioLoop(duration=duration)])
        return afx.audio_loop(audio_clip, duration=duration)

    def render(
        self,
        browser_video_path: str,
        timeline: list[dict],
        output_mp4_path: str,
        output_srt_path: str,
        cut_start_sec: float = 0.0,
        bgm_path: str = "trilha.mp3",
        logger=None,
    ) -> None:
        video = None
        audio_clips = []
        try:
            video = VideoFileClip(browser_video_path)
            if cut_start_sec and cut_start_sec > 0:
                video = self._subclip(video, cut_start_sec)

            if os.path.exists(bgm_path):
                bgm = AudioFileClip(bgm_path)
                bgm = self._scale_volume(bgm, 0.08)
                bgm = self._loop_audio(bgm, duration=video.duration)
                audio_clips.append(bgm)

            for item in timeline:
                audio_file = item.get("audio_file")
                if audio_file and os.path.exists(audio_file):
                    clip = AudioFileClip(audio_file)
                    clip = self._set_audio_start(clip, float(item["start_sec"]))
                    audio_clips.append(clip)

            if audio_clips:
                video = self._set_audio(video, CompositeAudioClip(audio_clips))

            output_mp4 = Path(output_mp4_path)
            output_srt = Path(output_srt_path)
            output_mp4.parent.mkdir(parents=True, exist_ok=True)
            output_srt.parent.mkdir(parents=True, exist_ok=True)

            video.write_videofile(
                str(output_mp4),
                codec="libx264",
                audio_codec="aac",
                fps=24,
                preset="ultrafast",
                logger=logger,
            )

            SubtitleWriter().write_srt(timeline, str(output_srt))
        finally:
            if video:
                try:
                    video.close()
                except Exception:
                    pass
            for clip in audio_clips:
                try:
                    clip.close()
                except Exception:
                    pass