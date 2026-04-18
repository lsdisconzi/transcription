"""Domain entities — depend on NOTHING external."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Speaker:
    """Identified speaker label from diarization."""
    label: str  # e.g. "SPEAKER_00"


@dataclass(frozen=True)
class Segment:
    """A single transcribed audio segment."""
    index: int
    speaker: Speaker
    start: float
    end: float
    text: str = ""

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)


@dataclass(frozen=True)
class DiarizationTurn:
    """A raw diarization turn (before transcription)."""
    speaker: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)


@dataclass
class Transcript:
    """Complete transcription result."""
    transcript_id: str
    segments: list[Segment] = field(default_factory=list)
    source_file: str = ""
    language: str = "es"
    metadata: dict = field(default_factory=dict)
    timestamp: str = ""
    provider: str = ""
    original_transcript_id: str = ""


@dataclass(frozen=True)
class AudioFile:
    """Value object representing an audio file on disk."""
    path: str
    format: str = "wav"

    @property
    def exists(self) -> bool:
        import os
        return os.path.exists(self.path)
