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
        segments = [
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
        data = {
            "transcript_id": transcript.transcript_id,
            "source_file": transcript.source_file or "",
            "language": transcript.language or "",
            "timestamp": transcript.timestamp or "",
            "provider": transcript.provider or "",
            "original_transcript_id": transcript.original_transcript_id or "",
            "metadata": transcript.metadata or {},
            "segments": segments,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"[store] saved {path} segments={len(segments)}")
        return path

    def load(self, transcript_id: str) -> Transcript | None:
        path = os.path.join(self._dir, f"{transcript_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        # Backward compat: legacy files stored a flat list of segments.
        if isinstance(raw, list):
            items = raw
            meta = {}
            source_file = ""
            language = "es"
            timestamp = ""
            provider = ""
            original_transcript_id = ""
        else:
            items = raw.get("segments", []) or []
            meta = raw.get("metadata", {}) or {}
            source_file = raw.get("source_file", "") or ""
            language = raw.get("language", "es") or "es"
            timestamp = raw.get("timestamp", "") or ""
            provider = raw.get("provider", "") or ""
            original_transcript_id = raw.get("original_transcript_id", "") or ""

        segments = [
            Segment(
                index=item["index"],
                speaker=Speaker(label=item["speaker"]),
                start=item["start"],
                end=item["end"],
                text=item.get("text", ""),
            )
            for item in items
        ]
        return Transcript(
            transcript_id=transcript_id,
            segments=segments,
            source_file=source_file,
            language=language,
            metadata=meta,
            timestamp=timestamp,
            provider=provider,
            original_transcript_id=original_transcript_id,
        )

    def list_ids(self) -> list[str]:
        return [
            f.replace(".json", "")
            for f in os.listdir(self._dir)
            if f.endswith(".json")
        ]
