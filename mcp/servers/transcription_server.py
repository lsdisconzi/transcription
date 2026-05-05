"""transcription MCP transcription server (bootstrap standard).

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

mcp = FastMCP("transcription-transcription")


@mcp.tool()
async def transcription_transcribe_audio(
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
async def transcription_transcribe_audio_async(
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
async def transcription_transcribe_audio_guided(
    file_path: str | None = None,
    audio_base64: str | None = None,
    filename: str | None = None,
    canonical_name: str | None = None,
    project_id: str | None = None,
    top_n_references: int = 3,
    language: str = "es",
    model_size: str = "large-v3",
    min_speakers: int = 1,
    max_speakers: int = 4,
    vad_threshold: float = 0.25,
    noise_reduce: bool = True,
    reduction_db: int = 25,
    voice_enhance: bool = True,
    apply_gain: bool = True,
    target_lufs: float = -16.0,
    remove_silence: bool = True,
    silence_thresh: int = -45,
    min_silence_len: int = 250,
    beam_size: int = 5,
    best_of: int = 5,
    whisper_temp: float = 0.0,
    condition_on_previous_text: bool = False,
    word_timestamps: bool = False,
) -> dict[str, Any]:
    """Run reference-guided transcription and return transcript payload."""
    return await src_transcription.transcribe_audio_guided(
        file_path=file_path,
        audio_base64=audio_base64,
        filename=filename,
        canonical_name=canonical_name,
        project_id=project_id,
        top_n_references=top_n_references,
        language=language,
        model_size=model_size,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        vad_threshold=vad_threshold,
        noise_reduce=noise_reduce,
        reduction_db=reduction_db,
        voice_enhance=voice_enhance,
        apply_gain=apply_gain,
        target_lufs=target_lufs,
        remove_silence=remove_silence,
        silence_thresh=silence_thresh,
        min_silence_len=min_silence_len,
        beam_size=beam_size,
        best_of=best_of,
        whisper_temp=whisper_temp,
        condition_on_previous_text=condition_on_previous_text,
        word_timestamps=word_timestamps,
    )


@mcp.tool()
async def transcription_transcribe_audio_guided_async(
    file_path: str | None = None,
    audio_base64: str | None = None,
    filename: str | None = None,
    canonical_name: str | None = None,
    project_id: str | None = None,
    top_n_references: int = 3,
    language: str = "es",
    model_size: str = "large-v3",
    min_speakers: int = 1,
    max_speakers: int = 4,
    vad_threshold: float = 0.25,
) -> dict[str, Any]:
    """Queue guided transcription and return asynchronous job state."""
    return await src_transcription.transcribe_audio_guided_async(
        file_path=file_path,
        audio_base64=audio_base64,
        filename=filename,
        canonical_name=canonical_name,
        project_id=project_id,
        top_n_references=top_n_references,
        language=language,
        model_size=model_size,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        vad_threshold=vad_threshold,
    )


@mcp.tool()
def transcription_get_transcription_job(job_id: str) -> dict[str, Any]:
    """Return current status for an async transcription job."""
    return src_transcription.get_transcription_job(job_id)


@mcp.tool()
def transcription_stream_transcription_job(job_id: str, cursor: int = 0) -> dict[str, Any]:
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
def transcription_diarize_excerpt(
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
def transcription_diarize_excerpt_by_path(
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
