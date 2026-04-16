"""JSON transcript store adapter — implements TranscriptStorePort."""
from __future__ import annotations

import json
import logging
import os

from src.domain.entities.transcript import Segment, Speaker, Transcript

logger = logging.getLogger(__name__)


class JSONTranscriptStore:
    """Persist transcripts as JSON files. Implements TranscriptStorePort."""

    def __init__(self, transcript_dir: str):
        self._dir = transcript_dir
        os.makedirs(self._dir, exist_ok=True)

    def save(self, transcript: Transcript) -> str:
        path = os.path.join(self._dir, f"{transcript.transcript_id}.json")
        data = [
            {
                "index": seg.index,
                "speaker": seg.speaker.label,
                "start": seg.start,
                "end": seg.end,
                "duration": seg.duration,
                "text": seg.text,
            }
            for seg in transcript.segments
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"[store] saved {path}")
        return path

    def load(self, transcript_id: str) -> Transcript | None:
        path = os.path.join(self._dir, f"{transcript_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        segments = [
            Segment(
                index=item["index"],
                speaker=Speaker(label=item["speaker"]),
                start=item["start"],
                end=item["end"],
                text=item.get("text", ""),
            )
            for item in data
        ]
        return Transcript(transcript_id=transcript_id, segments=segments)

    def list_ids(self) -> list[str]:
        return [
            f.replace(".json", "")
            for f in os.listdir(self._dir)
            if f.endswith(".json")
        ]
