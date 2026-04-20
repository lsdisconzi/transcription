"""Pinocchio MCP server: transcription and diarization tools.

Launch with:
    python -m src.mcp.servers.transcription_server
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.composition import build_runtime
from src.config import settings
from src.presentation.middleware.path_validator import validate_file_path

logger = logging.getLogger(__name__)


def _decode_audio_input(
    *,
    file_path: str | None,
    audio_base64: str | None,
    filename: str | None,
) -> tuple[str, bytes]:
    """Normalize audio input to (filename, bytes)."""
    if bool(file_path) == bool(audio_base64):
        raise ValueError("Provide exactly one of 'file_path' or 'audio_base64'.")

    if file_path:
        resolved = validate_file_path(file_path)
        return resolved.name, resolved.read_bytes()

    assert audio_base64 is not None
    try:
        content = base64.b64decode(audio_base64, validate=True)
    except Exception as exc:
        raise ValueError("Invalid audio_base64 payload.") from exc

    effective_name = (filename or "audio_upload.wav").strip() or "audio_upload.wav"
    return effective_name, content


def _decode_audio_to_tempfile(
    *,
    file_path: str | None,
    audio_base64: str | None,
    filename: str | None,
) -> tuple[str, list[str]]:
    """Return a usable file path for excerpt diarization plus cleanup paths."""
    cleanup_paths: list[str] = []

    if bool(file_path) == bool(audio_base64):
        raise ValueError("Provide exactly one of 'file_path' or 'audio_base64'.")

    if file_path:
        resolved = validate_file_path(file_path)
        source_path = str(resolved)
    else:
        assert audio_base64 is not None
        try:
            content = base64.b64decode(audio_base64, validate=True)
        except Exception as exc:
            raise ValueError("Invalid audio_base64 payload.") from exc

        suffix = Path((filename or "audio_upload.wav")).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            source_path = tmp.name
            cleanup_paths.append(tmp.name)

    ext = Path(source_path).suffix.lower()
    if ext != ".wav":
        wav_path = _AUDIO_FILES.convert_to_wav(source_path)
        cleanup_paths.append(wav_path)
        source_path = wav_path

    return source_path, cleanup_paths


def _build_transcribe_params(
    *,
    language: str,
    model_size: str,
    min_speakers: int,
    max_speakers: int,
    vad_threshold: float,
    noise_reduce: bool,
    reduction_db: int,
    voice_enhance: bool,
    apply_gain: bool,
    target_lufs: float,
    remove_silence: bool,
    silence_thresh: int,
    min_silence_len: int,
    beam_size: int,
    best_of: int,
    whisper_temp: float,
    temperature_increment_on_fallback: float,
    compression_ratio_threshold: float,
    logprob_threshold: float,
    no_speech_threshold: float,
    condition_on_previous_text: bool,
    initial_prompt: str | None,
    length_penalty: float,
    patience: float | None,
    suppress_blank: bool,
    suppress_tokens: str,
    word_timestamps: bool,
    keep_cache: bool,
    progress_callback,
) -> dict[str, Any]:
    return {
        "language": language,
        "model_size": model_size,
        "min_speakers": min_speakers,
        "max_speakers": max_speakers,
        "vad_threshold": vad_threshold,
        "noise_reduce": noise_reduce,
        "reduction_db": reduction_db,
        "voice_enhance": voice_enhance,
        "apply_gain": apply_gain,
        "target_lufs": target_lufs,
        "remove_silence": remove_silence,
        "silence_thresh": silence_thresh,
        "min_silence_len": min_silence_len,
        "beam_size": beam_size,
        "best_of": best_of,
        "whisper_temp": whisper_temp,
        "temperature_increment_on_fallback": temperature_increment_on_fallback,
        "compression_ratio_threshold": compression_ratio_threshold,
        "logprob_threshold": logprob_threshold,
        "no_speech_threshold": no_speech_threshold,
        "condition_on_previous_text": condition_on_previous_text,
        "initial_prompt": initial_prompt,
        "length_penalty": length_penalty,
        "patience": patience,
        "suppress_blank": suppress_blank,
        "suppress_tokens": suppress_tokens,
        "word_timestamps": word_timestamps,
        "keep_cache": keep_cache,
        "progress_callback": progress_callback,
    }


@dataclass
class JobState:
    job_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "Queued"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: dict[str, Any] | None = None
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


def _job_public(job: JobState) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "result": job.result,
        "error": job.error,
        "events": job.events,
    }


_RUNTIME = build_runtime()
_TRANSCRIBE_USE_CASE = _RUNTIME.transcribe_use_case
_EXCERPT_USE_CASE = _RUNTIME.excerpt_use_case
_AUDIO_FILES = _RUNTIME.audio_file_adapter
_JOBS: dict[str, JobState] = {}

mcp = FastMCP("pinocchio-transcription")


@mcp.tool()
async def transcribe_audio(
    file_path: str | None = None,
    audio_base64: str | None = None,
    filename: str | None = None,
    language: str = "es-CL",
    model_size: str = "large-v3",
    min_speakers: int = 1,
    max_speakers: int = 2,
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
    temperature_increment_on_fallback: float = 0.2,
    compression_ratio_threshold: float = 2.4,
    logprob_threshold: float = -1.0,
    no_speech_threshold: float = 0.6,
    condition_on_previous_text: bool = False,
    initial_prompt: str | None = None,
    length_penalty: float = 1.0,
    patience: float | None = None,
    suppress_blank: bool = True,
    suppress_tokens: str = "-1",
    word_timestamps: bool = False,
    keep_cache: bool = True,
    include_progress_events: bool = False,
) -> dict[str, Any]:
    """Run full transcription (diarization + ASR) and return transcript result."""
    input_filename, content = _decode_audio_input(
        file_path=file_path,
        audio_base64=audio_base64,
        filename=filename,
    )
    events: list[dict[str, Any]] = []

    def progress_callback(stage: str, progress: int, message: str, extra: dict | None = None):
        if include_progress_events:
            events.append(
                {
                    "stage": stage,
                    "progress": progress,
                    "message": message,
                    "extra": extra or {},
                    "timestamp": time.time(),
                }
            )

    params = _build_transcribe_params(
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
        temperature_increment_on_fallback=temperature_increment_on_fallback,
        compression_ratio_threshold=compression_ratio_threshold,
        logprob_threshold=logprob_threshold,
        no_speech_threshold=no_speech_threshold,
        condition_on_previous_text=condition_on_previous_text,
        initial_prompt=initial_prompt,
        length_penalty=length_penalty,
        patience=patience,
        suppress_blank=suppress_blank,
        suppress_tokens=suppress_tokens,
        word_timestamps=word_timestamps,
        keep_cache=keep_cache,
        progress_callback=progress_callback,
    )

    result = await _TRANSCRIBE_USE_CASE.execute(
        filename=input_filename,
        content=content,
        dest_dir=settings.ORIGINALS_DIR,
        params=params,
    )

    payload = result.model_dump()
    if include_progress_events:
        payload["progress_events"] = events
    return payload


async def _run_transcription_job(job: JobState, kwargs: dict[str, Any]) -> None:
    def progress_callback(stage: str, progress: int, message: str, extra: dict | None = None):
        job.status = "running"
        job.progress = max(0, min(100, int(progress)))
        job.message = message
        job.updated_at = time.time()
        job.events.append(
            {
                "stage": stage,
                "progress": job.progress,
                "message": message,
                "extra": extra or {},
                "timestamp": job.updated_at,
            }
        )

    try:
        params = _build_transcribe_params(
            language=kwargs["language"],
            model_size=kwargs["model_size"],
            min_speakers=kwargs["min_speakers"],
            max_speakers=kwargs["max_speakers"],
            vad_threshold=kwargs["vad_threshold"],
            noise_reduce=kwargs["noise_reduce"],
            reduction_db=kwargs["reduction_db"],
            voice_enhance=kwargs["voice_enhance"],
            apply_gain=kwargs["apply_gain"],
            target_lufs=kwargs["target_lufs"],
            remove_silence=kwargs["remove_silence"],
            silence_thresh=kwargs["silence_thresh"],
            min_silence_len=kwargs["min_silence_len"],
            beam_size=kwargs["beam_size"],
            best_of=kwargs["best_of"],
            whisper_temp=kwargs["whisper_temp"],
            temperature_increment_on_fallback=kwargs["temperature_increment_on_fallback"],
            compression_ratio_threshold=kwargs["compression_ratio_threshold"],
            logprob_threshold=kwargs["logprob_threshold"],
            no_speech_threshold=kwargs["no_speech_threshold"],
            condition_on_previous_text=kwargs["condition_on_previous_text"],
            initial_prompt=kwargs["initial_prompt"],
            length_penalty=kwargs["length_penalty"],
            patience=kwargs["patience"],
            suppress_blank=kwargs["suppress_blank"],
            suppress_tokens=kwargs["suppress_tokens"],
            word_timestamps=kwargs["word_timestamps"],
            keep_cache=kwargs["keep_cache"],
            progress_callback=progress_callback,
        )

        result = await _TRANSCRIBE_USE_CASE.execute(
            filename=kwargs["input_filename"],
            content=kwargs["content"],
            dest_dir=settings.ORIGINALS_DIR,
            params=params,
        )
        job.status = "done"
        job.progress = 100
        job.message = "Completed"
        job.result = result.model_dump()
        job.updated_at = time.time()
    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
        job.message = f"Error: {exc}"
        job.updated_at = time.time()
        logger.exception("[mcp] async transcription job failed")


@mcp.tool()
async def transcribe_audio_async(
    file_path: str | None = None,
    audio_base64: str | None = None,
    filename: str | None = None,
    language: str = "es-CL",
    model_size: str = "large-v3",
    min_speakers: int = 1,
    max_speakers: int = 2,
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
    temperature_increment_on_fallback: float = 0.2,
    compression_ratio_threshold: float = 2.4,
    logprob_threshold: float = -1.0,
    no_speech_threshold: float = 0.6,
    condition_on_previous_text: bool = False,
    initial_prompt: str | None = None,
    length_penalty: float = 1.0,
    patience: float | None = None,
    suppress_blank: bool = True,
    suppress_tokens: str = "-1",
    word_timestamps: bool = False,
    keep_cache: bool = True,
) -> dict[str, Any]:
    """Queue full transcription and return a job id for polling."""
    input_filename, content = _decode_audio_input(
        file_path=file_path,
        audio_base64=audio_base64,
        filename=filename,
    )

    job_id = str(uuid.uuid4())
    job = JobState(job_id=job_id)
    _JOBS[job_id] = job

    task_kwargs = {
        "input_filename": input_filename,
        "content": content,
        "language": language,
        "model_size": model_size,
        "min_speakers": min_speakers,
        "max_speakers": max_speakers,
        "vad_threshold": vad_threshold,
        "noise_reduce": noise_reduce,
        "reduction_db": reduction_db,
        "voice_enhance": voice_enhance,
        "apply_gain": apply_gain,
        "target_lufs": target_lufs,
        "remove_silence": remove_silence,
        "silence_thresh": silence_thresh,
        "min_silence_len": min_silence_len,
        "beam_size": beam_size,
        "best_of": best_of,
        "whisper_temp": whisper_temp,
        "temperature_increment_on_fallback": temperature_increment_on_fallback,
        "compression_ratio_threshold": compression_ratio_threshold,
        "logprob_threshold": logprob_threshold,
        "no_speech_threshold": no_speech_threshold,
        "condition_on_previous_text": condition_on_previous_text,
        "initial_prompt": initial_prompt,
        "length_penalty": length_penalty,
        "patience": patience,
        "suppress_blank": suppress_blank,
        "suppress_tokens": suppress_tokens,
        "word_timestamps": word_timestamps,
        "keep_cache": keep_cache,
    }
    asyncio.create_task(_run_transcription_job(job, task_kwargs))
    return _job_public(job)


@mcp.tool()
def get_transcription_job(job_id: str) -> dict[str, Any]:
    """Fetch current status/result for an async transcription job."""
    job = _JOBS.get(job_id)
    if job is None:
        raise ValueError(f"Job not found: {job_id}")
    return _job_public(job)


@mcp.tool()
def diarize_excerpt(
    start: float,
    end: float,
    file_path: str | None = None,
    audio_base64: str | None = None,
    filename: str | None = None,
    min_speakers: int = 1,
    max_speakers: int = 2,
    num_speakers: int | None = None,
) -> dict[str, Any]:
    """Diarize a single excerpt by path or base64 audio payload."""
    if start < 0 or end <= start:
        raise ValueError("Invalid time range. Ensure start >= 0 and end > start.")

    source_path = ""
    cleanup_paths: list[str] = []
    try:
        source_path, cleanup_paths = _decode_audio_to_tempfile(
            file_path=file_path,
            audio_base64=audio_base64,
            filename=filename,
        )
        result = _EXCERPT_USE_CASE.execute(
            file_path=source_path,
            start=start,
            end=end,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            num_speakers=num_speakers,
        )
        return result.model_dump()
    finally:
        for path in cleanup_paths:
            if path and os.path.exists(path):
                with contextlib.suppress(Exception):
                    os.remove(path)


def main() -> None:
    """Entrypoint for stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
