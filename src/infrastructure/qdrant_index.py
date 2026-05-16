"""Qdrant transcript index — implements TranscriptIndexPort."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.domain.entities.transcript import Transcript

logger = logging.getLogger(__name__)

COLLECTION = "transcription_transcripts"
VECTOR_DIM = 384  # all-MiniLM-L6-v2 output dimension


class QdrantTranscriptIndex:
    """Index and search transcript segments in Qdrant. Implements TranscriptIndexPort."""

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: str | None = None,
    ):
        normalized_url = self._normalize_qdrant_url(url)
        normalized_key = self._normalize_qdrant_api_key(api_key)
        self._client = QdrantClient(url=normalized_url, api_key=normalized_key or None)
        self._encoder = None  # lazy-loaded
        self._ensure_collection()

    @staticmethod
    def _normalize_qdrant_url(raw_url: str) -> str:
        value = (raw_url or "").strip()
        if not value:
            return ""

        parsed = urlparse(value if "://" in value else f"https://{value}")
        if parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return value

    @staticmethod
    def _normalize_qdrant_api_key(raw_key: str | None) -> str:
        key = (raw_key or "").strip()
        if not key:
            return ""

        if "|" not in key:
            return key

        parts = [p.strip() for p in key.split("|") if p.strip()]
        if not parts:
            return key
        return max(parts, key=len)

    def _ensure_collection(self) -> None:
        collections = [c.name for c in self._client.get_collections().collections]
        if COLLECTION not in collections:
            self._client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )
            logger.info("[qdrant] created collection %s", COLLECTION)

    def _get_encoder(self):
        """Lazy-load the sentence transformer on first use."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[qdrant] loaded embedding model all-MiniLM-L6-v2")
        return self._encoder

    def _make_point_id(self, transcript_id: str, segment_index: int) -> str:
        """Deterministic UUID-compatible hex id from transcript + segment."""
        raw = f"{transcript_id}:{segment_index}"
        return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324

    async def index(self, transcript: Transcript) -> int:
        """Index all segments of a transcript. Returns number of points upserted."""
        if not transcript.segments:
            return 0

        encoder = await asyncio.to_thread(self._get_encoder)

        texts = [seg.text for seg in transcript.segments]
        embeddings = await asyncio.to_thread(encoder.encode, texts)

        points = []
        for seg, emb in zip(transcript.segments, embeddings, strict=False):
            point_id = self._make_point_id(transcript.transcript_id, seg.index)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb.tolist(),
                    payload={
                        "transcript_id": transcript.transcript_id,
                        "segment_index": seg.index,
                        "speaker": seg.speaker.label,
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                        "source_file": transcript.source_file,
                        "language": transcript.language,
                    },
                )
            )

        await asyncio.to_thread(
            self._client.upsert,
            collection_name=COLLECTION,
            points=points,
        )

        logger.info(
            "[qdrant] indexed %d segments for transcript=%s",
            len(points),
            transcript.transcript_id,
        )
        return len(points)

    async def search(self, query: str, *, limit: int = 5) -> list[dict]:
        """Semantic search across all transcript segments."""
        encoder = await asyncio.to_thread(self._get_encoder)
        query_vector = await asyncio.to_thread(encoder.encode, query)

        results = await asyncio.to_thread(
            self._client.query_points,
            collection_name=COLLECTION,
            query=query_vector.tolist(),
            limit=limit,
        )

        return [
            {
                "transcript_id": hit.payload["transcript_id"],
                "segment_index": hit.payload["segment_index"],
                "speaker": hit.payload["speaker"],
                "start": hit.payload["start"],
                "end": hit.payload["end"],
                "text": hit.payload["text"],
                "source_file": hit.payload.get("source_file", ""),
                "score": hit.score,
            }
            for hit in results.points
        ]

    async def delete(self, transcript_id: str) -> None:
        """Remove all points for a given transcript."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        await asyncio.to_thread(
            self._client.delete,
            collection_name=COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="transcript_id",
                        match=MatchValue(value=transcript_id),
                    )
                ]
            ),
        )
        logger.info("[qdrant] deleted vectors for transcript=%s", transcript_id)
