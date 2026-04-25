"""transcription MCP server: transcript intelligence and indexing tools.

Launch with:
    python -m src.mcp.servers.transcripts_server
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.composition import build_runtime
from src.domain.entities.transcript import Segment, Speaker, Transcript

logger = logging.getLogger(__name__)

_RUNTIME = build_runtime()
_ANALYZE_USE_CASE = _RUNTIME.analyze_use_case
_SEARCH_USE_CASE = _RUNTIME.search_use_case
_STORE = _RUNTIME.store_adapter
_INDEX = _RUNTIME.qdrant_adapter

mcp = FastMCP("transcription-transcripts")

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename_stem(name: str) -> str:
    """Turn user-facing filename into a safe transcript_id stem."""
    if not name:
        return ""
    base = os.path.basename(str(name)).strip()
    stem, _ext = os.path.splitext(base)
    cleaned = _SAFE_NAME_RE.sub("_", stem).strip("._-")
    return cleaned[:180]


def _serialize_transcript(transcript: Transcript) -> dict[str, Any]:
    return {
        "transcript_id": transcript.transcript_id,
        "source_file": transcript.source_file,
        "language": transcript.language,
        "timestamp": transcript.timestamp,
        "provider": transcript.provider,
        "original_transcript_id": transcript.original_transcript_id,
        "metadata": transcript.metadata or {},
        "segments": [
            {
                "index": s.index,
                "speaker": s.speaker.label,
                "start": s.start,
                "end": s.end,
                "duration": s.duration,
                "text": s.text,
            }
            for s in transcript.segments
        ],
    }


@mcp.tool()
def list_transcripts() -> dict[str, Any]:
    """Return all transcript ids, newest first by id sort."""
    return {"transcripts": sorted(_STORE.list_ids(), reverse=True)}


@mcp.tool()
def get_transcript(transcript_id: str) -> dict[str, Any]:
    """Load one transcript by id."""
    transcript = _STORE.load(transcript_id)
    if transcript is None:
        raise ValueError(f"Transcript not found: {transcript_id}")
    return _serialize_transcript(transcript)


@mcp.tool()
def import_transcripts(
    runs: list[dict[str, Any]],
    overwrite: bool = False,
    rename_by_filename: bool = True,
) -> dict[str, Any]:
    """Import one or more transcript runs into JSON transcript storage."""
    if not runs:
        raise ValueError("No runs provided for import")

    existing_ids = set(_STORE.list_ids())
    imported_ids: list[str] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, run in enumerate(runs):
        try:
            segments_payload = run.get("segments") or []
            segments: list[Segment] = []
            for seg_idx, seg in enumerate(segments_payload):
                start = float(seg.get("start") or 0.0)
                if start < 0:
                    start = 0.0

                end_raw = seg.get("end") if seg.get("end") is not None else start
                end = float(end_raw)
                if end < start:
                    end = start

                speaker_label = (seg.get("speaker") or f"SPEAKER_{seg_idx:02d}").strip() or f"SPEAKER_{seg_idx:02d}"
                segment_index = seg.get("index") if seg.get("index") is not None else seg_idx

                segments.append(
                    Segment(
                        index=int(segment_index),
                        speaker=Speaker(label=speaker_label),
                        start=start,
                        end=end,
                        text=str(seg.get("text") or ""),
                    )
                )

            if not segments:
                skipped.append({"index": idx, "reason": "empty_segments"})
                continue

            incoming_id = str(run.get("transcript_id") or "").strip()
            source_file = str(run.get("source_file") or run.get("filename") or "").strip()
            filename_stem = _sanitize_filename_stem(str(run.get("filename") or run.get("source_file") or ""))

            if rename_by_filename and filename_stem:
                desired_id = filename_stem
            elif incoming_id:
                desired_id = incoming_id
            elif filename_stem:
                desired_id = filename_stem
            else:
                desired_id = f"imported_{int(time.time() * 1000)}_{idx + 1}"

            transcript_id = desired_id
            if not overwrite and transcript_id in existing_ids:
                nonce = 1
                while transcript_id in existing_ids:
                    nonce += 1
                    transcript_id = f"{desired_id}_{nonce}"

            if not overwrite and transcript_id in existing_ids:
                skipped.append(
                    {
                        "index": idx,
                        "transcript_id": transcript_id,
                        "reason": "already_exists",
                    }
                )
                continue

            transcript = Transcript(
                transcript_id=transcript_id,
                segments=segments,
                source_file=source_file,
                language=(str(run.get("language") or "es") or "es"),
                metadata=(run.get("metadata") or {}),
                timestamp=str(run.get("timestamp") or ""),
                provider=str(run.get("provider") or ""),
                original_transcript_id=(incoming_id if incoming_id and incoming_id != transcript_id else ""),
            )
            _STORE.save(transcript)
            existing_ids.add(transcript_id)
            imported_ids.append(transcript_id)
        except Exception as exc:
            errors.append(
                {
                    "index": idx,
                    "transcript_id": run.get("transcript_id"),
                    "error": str(exc),
                }
            )

    return {
        "total_runs": len(runs),
        "imported": len(imported_ids),
        "imported_ids": imported_ids,
        "skipped": skipped,
        "errors": errors,
    }


@mcp.tool()
async def analyze_transcript(transcript_id: str, instructions: str = "") -> dict[str, Any]:
    """Run configured LLM analyzer for one transcript."""
    if _ANALYZE_USE_CASE is None:
        raise ValueError("Transcript analysis not configured. Set DEEPSEEK_API_KEY or ANTHROPIC_API_KEY.")
    result = await _ANALYZE_USE_CASE.execute(transcript_id, instructions=instructions)
    return result.model_dump()


@mcp.tool()
async def search_transcripts(query: str, limit: int = 5) -> dict[str, Any]:
    """Semantic search across all indexed transcript segments."""
    if _SEARCH_USE_CASE is None:
        raise ValueError("Transcript search not configured. Set QDRANT_URL.")
    result = await _SEARCH_USE_CASE.execute(query, limit=limit)
    return result.model_dump()


@mcp.tool()
async def index_transcript(transcript_id: str) -> dict[str, Any]:
    """Re-index a single transcript into Qdrant."""
    if _INDEX is None:
        raise ValueError("Vector indexing not configured. Set QDRANT_URL.")
    transcript = _STORE.load(transcript_id)
    if transcript is None:
        raise ValueError(f"Transcript not found: {transcript_id}")
    count = await _INDEX.index(transcript)
    return {"transcript_id": transcript_id, "segments_indexed": count}


@mcp.tool()
async def index_all_transcripts() -> dict[str, Any]:
    """Re-index all stored transcripts into Qdrant."""
    if _INDEX is None:
        raise ValueError("Vector indexing not configured. Set QDRANT_URL.")

    ids = _STORE.list_ids()
    total = 0
    errors: list[dict[str, Any]] = []

    for transcript_id in ids:
        transcript = _STORE.load(transcript_id)
        if transcript is None:
            continue
        try:
            count = await _INDEX.index(transcript)
            total += count
        except Exception as exc:
            errors.append({"transcript_id": transcript_id, "error": str(exc)})

    return {
        "transcripts_processed": len(ids),
        "segments_indexed": total,
        "errors": errors,
    }


def main() -> None:
    """Entrypoint for stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
