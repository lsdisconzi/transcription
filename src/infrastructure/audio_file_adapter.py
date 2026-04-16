"""Audio file operations adapter — implements AudioFilePort."""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from pydub import AudioSegment

logger = logging.getLogger(__name__)


class AudioFileAdapter:
    """File I/O for audio uploads/conversions. Implements AudioFilePort."""

    async def save_upload(self, filename: str, content: bytes, dest_dir: str) -> str:
        safe_name = Path(filename).name
        timestamp = int(time.time())
        base, ext = os.path.splitext(safe_name)
        out_path = os.path.join(dest_dir, f"{base}_{timestamp}{ext}")
        with open(out_path, "wb") as f:
            f.write(content)
        return out_path

    def convert_to_wav(self, audio_path: str) -> str:
        if audio_path.lower().endswith(".wav"):
            return audio_path
        audio = AudioSegment.from_file(audio_path)
        wav_path = audio_path + ".wav"
        audio.export(wav_path, format="wav")
        os.remove(audio_path)
        return wav_path

    def crop_audio(self, audio_path: str, start: float, end: float):
        from pyannote.audio import Audio as PyAudio
        from pyannote.core import Segment

        waveform, sample_rate = PyAudio().crop(audio_path, Segment(start, end))
        return waveform, sample_rate

    def get_duration(self, audio_path: str) -> float:
        audio = AudioSegment.from_file(audio_path)
        return audio.duration_seconds

    def extract_segment(
        self, audio_path: str, start_ms: int, end_ms: int, out_path: str
    ) -> str:
        full_audio = AudioSegment.from_wav(audio_path)
        segment = full_audio[start_ms:end_ms]
        segment.export(out_path, format="wav")
        return out_path
