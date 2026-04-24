"""Pinocchio MCP transcription server (bootstrap standard).

Launch with:
    python mcp/servers/transcription_server.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mcp.servers import transcription_server as src_transcription

mcp = FastMCP("pinocchio-transcription")


@mcp.tool()
async def pinocchio_transcribe_audio(
    file_path: str | None = None,
    audio_base64: str | None = None,
    filename: str | None = None,
    language: str = "es-CL",
    model_size: str = "large-v3",
    min_speakers: int = 1,
    max_speakers: int = 2,
    include_progress_events: bool = False,
    keep_cache: bool = True,
) -> dict[str, Any]:
    """Run full transcription and return transcript payload."""
    return await src_transcription.transcribe_audio(
        file_path=file_path,
        audio_base64=audio_base64,
        filename=filename,
        language=language,
        model_size=model_size,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        include_progress_events=include_progress_events,
        keep_cache=keep_cache,
    )


@mcp.tool()
async def pinocchio_transcribe_audio_async(
    file_path: str | None = None,
    audio_base64: str | None = None,
    filename: str | None = None,
    language: str = "es-CL",
    model_size: str = "large-v3",
    min_speakers: int = 1,
    max_speakers: int = 2,
    keep_cache: bool = True,
) -> dict[str, Any]:
    """Queue transcription and return asynchronous job state."""
    return await src_transcription.transcribe_audio_async(
        file_path=file_path,
        audio_base64=audio_base64,
        filename=filename,
        language=language,
        model_size=model_size,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        keep_cache=keep_cache,
    )


@mcp.tool()
def pinocchio_get_transcription_job(job_id: str) -> dict[str, Any]:
    """Return current status for an async transcription job."""
    return src_transcription.get_transcription_job(job_id)


@mcp.tool()
def pinocchio_stream_transcription_job(job_id: str, cursor: int = 0) -> dict[str, Any]:
    """Return incremental job events as an MCP-safe stream snapshot."""
    job = src_transcription.get_transcription_job(job_id)
    events = job.get("events") or []
    start = max(0, int(cursor))
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "message": job.get("message"),
        "events": events[start:],
        "next_cursor": len(events),
        "done": job.get("status") in {"done", "error"},
    }


@mcp.tool()
def pinocchio_diarize_excerpt(
    start: float,
    end: float,
    file_path: str | None = None,
    audio_base64: str | None = None,
    filename: str | None = None,
    min_speakers: int = 1,
    max_speakers: int = 2,
    num_speakers: int | None = None,
) -> dict[str, Any]:
    """Diarize one excerpt from file path or base64 audio payload."""
    return src_transcription.diarize_excerpt(
        start=start,
        end=end,
        file_path=file_path,
        audio_base64=audio_base64,
        filename=filename,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        num_speakers=num_speakers,
    )


@mcp.tool()
def pinocchio_diarize_excerpt_by_path(
    file_path: str,
    start: float,
    end: float,
    min_speakers: int = 1,
    max_speakers: int = 2,
    num_speakers: int | None = None,
) -> dict[str, Any]:
    """Diarize one excerpt using a server-side audio file path."""
    return src_transcription.diarize_excerpt(
        start=start,
        end=end,
        file_path=file_path,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        num_speakers=num_speakers,
    )


def main() -> None:
    """Entrypoint for stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
