"""Integration tests for JSON transcript store."""
from __future__ import annotations

import json

from src.domain.entities.transcript import Segment, Speaker, Transcript
from src.infrastructure.json_store import JSONTranscriptStore


class TestJSONTranscriptStore:
    def test_save_and_load(self, tmp_path):
        store = JSONTranscriptStore(str(tmp_path))
        transcript = Transcript(
            transcript_id="test_001",
            segments=[
                Segment(index=1, speaker=Speaker("SPEAKER_00"), start=0.0, end=2.5, text="Hola"),
                Segment(index=2, speaker=Speaker("SPEAKER_01"), start=2.5, end=5.0, text="Chao"),
            ],
            source_file="test.wav",
            language="es",
        )

        path = store.save(transcript)
        assert path.endswith("test_001.json")

        loaded = store.load("test_001")
        assert loaded is not None
        assert loaded.transcript_id == "test_001"
        assert len(loaded.segments) == 2
        assert loaded.segments[0].text == "Hola"
        assert loaded.segments[0].speaker.label == "SPEAKER_00"
        assert loaded.segments[1].duration == 2.5

    def test_load_nonexistent_returns_none(self, tmp_path):
        store = JSONTranscriptStore(str(tmp_path))
        assert store.load("nonexistent") is None

    def test_list_ids(self, tmp_path):
        store = JSONTranscriptStore(str(tmp_path))

        # Save two transcripts
        for tid in ["t_100", "t_200"]:
            t = Transcript(transcript_id=tid, segments=[])
            store.save(t)

        ids = store.list_ids()
        assert set(ids) == {"t_100", "t_200"}

    def test_json_format(self, tmp_path):
        store = JSONTranscriptStore(str(tmp_path))
        transcript = Transcript(
            transcript_id="fmt_test",
            segments=[
                Segment(index=1, speaker=Speaker("A"), start=1.0, end=2.0, text="testing"),
            ],
        )
        store.save(transcript)

        with open(tmp_path / "fmt_test.json", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["speaker"] == "A"
        assert data[0]["text"] == "testing"
        assert data[0]["duration"] == 1.0

    def test_empty_transcript(self, tmp_path):
        store = JSONTranscriptStore(str(tmp_path))
        t = Transcript(transcript_id="empty_test", segments=[])
        store.save(t)

        loaded = store.load("empty_test")
        assert loaded is not None
        assert loaded.segments == []

    def test_unicode_text(self, tmp_path):
        store = JSONTranscriptStore(str(tmp_path))
        transcript = Transcript(
            transcript_id="unicode_test",
            segments=[
                Segment(index=1, speaker=Speaker("A"), start=0, end=1, text="Ñoño, ¿cómo estái?"),
            ],
        )
        store.save(transcript)
        loaded = store.load("unicode_test")
        assert loaded.segments[0].text == "Ñoño, ¿cómo estái?"
