"""Transcription router — thin presentation layer."""
from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .transcripts import (
    complete_progress_job,
    fail_progress_job,
    start_progress_job,
    update_progress_job,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/diarization", tags=["transcription"])

# Will be injected by main.py composition root
_transcribe_use_case = None
_originals_dir = None


def init_transcription_router(transcribe_use_case, originals_dir: str):
    global _transcribe_use_case, _originals_dir
    _transcribe_use_case = transcribe_use_case
    _originals_dir = originals_dir


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
) -> dict:
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
    }


@router.post("/transcribe")
async def diarization_transcribe(
    file: UploadFile = File(..., description="Audio file (wav, mp3, m4a, etc.)"),
    # General
    language: str = Form("es-CL", description="Locale code."),
    whisper_model: str = Form("large-v3", alias="model_size", description="Whisper model name."),
    min_speakers: int = Form(1, description="Minimum expected speakers."),
    max_speakers: int = Form(2, description="Maximum expected speakers."),
    vad_threshold: float = Form(0.25, description="Voice activity threshold."),
    # Preprocessing
    noise_reduce: bool = Form(True, description="Enable noise reduction."),
    reduction_db: int = Form(25, description="Noise reduction strength."),
    voice_enhance: bool = Form(True, description="Band-pass + compression."),
    apply_gain: bool = Form(True, description="Loudness normalization."),
    target_lufs: float = Form(-16.0, description="Target LUFS loudness."),
    remove_silence: bool = Form(True, description="Trim silence before diarization."),
    silence_thresh: int = Form(-45, description="Silence threshold dBFS."),
    min_silence_len: int = Form(250, description="Minimum silence length (ms)."),
    # Whisper decoding
    beam_size: int = Form(5, description="Beam search width."),
    best_of: int = Form(5, description="Number of candidates when sampling."),
    whisper_temp: float = Form(0.0, description="Sampling temperature."),
    temperature_increment_on_fallback: float = Form(0.2, description="Increment if retry."),
    compression_ratio_threshold: float = Form(2.4, description="Retry if too compressible."),
    logprob_threshold: float = Form(-1.0, description="Retry if avg logprob below."),
    no_speech_threshold: float = Form(0.6, description="Silence probability threshold."),
    condition_on_previous_text: bool = Form(False, description="Use prev text as context."),
    initial_prompt: str | None = Form(None, description="Optional priming text."),
    length_penalty: float = Form(1.0, description=">1 longer; <1 shorter."),
    patience: float | None = Form(None, description="Beam search patience."),
    suppress_blank: bool = Form(True, description="Suppress blank tokens."),
    suppress_tokens: str = Form("-1", description="Token IDs to suppress."),
    word_timestamps: bool = Form(False, description="Per-word timestamps."),
    # Control
    keep_cache: bool = Form(True, description="Keep loaded models cached."),
):
    try:
        content = await file.read()
        filename = file.filename or "audio_upload"

        params = _build_transcribe_params(
            language=language,
            model_size=whisper_model,
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
        )

        result = await _transcribe_use_case.execute(
            filename=filename,
            content=content,
            dest_dir=_originals_dir,
            params=params,
        )
        return result.model_dump()

    except Exception as e:
        logger.exception("[error] transcription failure")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/transcribe/async")
async def diarization_transcribe_async(
    file: UploadFile = File(..., description="Audio file (wav, mp3, m4a, etc.)"),
    # General
    language: str = Form("es-CL", description="Locale code."),
    whisper_model: str = Form("large-v3", alias="model_size", description="Whisper model name."),
    min_speakers: int = Form(1, description="Minimum expected speakers."),
    max_speakers: int = Form(2, description="Maximum expected speakers."),
    vad_threshold: float = Form(0.25, description="Voice activity threshold."),
    # Preprocessing
    noise_reduce: bool = Form(True, description="Enable noise reduction."),
    reduction_db: int = Form(25, description="Noise reduction strength."),
    voice_enhance: bool = Form(True, description="Band-pass + compression."),
    apply_gain: bool = Form(True, description="Loudness normalization."),
    target_lufs: float = Form(-16.0, description="Target LUFS loudness."),
    remove_silence: bool = Form(True, description="Trim silence before diarization."),
    silence_thresh: int = Form(-45, description="Silence threshold dBFS."),
    min_silence_len: int = Form(250, description="Minimum silence length (ms)."),
    # Whisper decoding
    beam_size: int = Form(5, description="Beam search width."),
    best_of: int = Form(5, description="Number of candidates when sampling."),
    whisper_temp: float = Form(0.0, description="Sampling temperature."),
    temperature_increment_on_fallback: float = Form(0.2, description="Increment if retry."),
    compression_ratio_threshold: float = Form(2.4, description="Retry if too compressible."),
    logprob_threshold: float = Form(-1.0, description="Retry if avg logprob below."),
    no_speech_threshold: float = Form(0.6, description="Silence probability threshold."),
    condition_on_previous_text: bool = Form(False, description="Use prev text as context."),
    initial_prompt: str | None = Form(None, description="Optional priming text."),
    length_penalty: float = Form(1.0, description=">1 longer; <1 shorter."),
    patience: float | None = Form(None, description="Beam search patience."),
    suppress_blank: bool = Form(True, description="Suppress blank tokens."),
    suppress_tokens: str = Form("-1", description="Token IDs to suppress."),
    word_timestamps: bool = Form(False, description="Per-word timestamps."),
    # Control
    keep_cache: bool = Form(True, description="Keep loaded models cached."),
):
    """Create async transcription job and return job_id for status/SSE tracking."""
    content = await file.read()
    filename = file.filename or "audio_upload"
    job_id = str(uuid.uuid4())

    start_progress_job(job_id, filename)

    params = _build_transcribe_params(
        language=language,
        model_size=whisper_model,
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
    )

    def _progress_callback(stage: str, progress: int, message: str, extra: dict | None = None):
        update_progress_job(
            job_id,
            stage=stage,
            progress=progress,
            message=message,
            extra=extra,
        )

    params["job_id"] = job_id
    params["progress_callback"] = _progress_callback

    async def _run_transcription_job():
        try:
            update_progress_job(job_id, stage="upload", progress=3, message="Upload recebido")
            result = await asyncio.to_thread(
                lambda: asyncio.run(
                    _transcribe_use_case.execute(
                        filename=filename,
                        content=content,
                        dest_dir=_originals_dir,
                        params=params,
                    )
                )
            )
            complete_progress_job(job_id, result.model_dump())
        except Exception as e:
            logger.exception("[error] async transcription failure job_id=%s", job_id)
            fail_progress_job(job_id, str(e))

    asyncio.create_task(_run_transcription_job())

    return {
        "job_id": job_id,
        "status": "queued",
        "status_url": f"/api/transcripts/status/{job_id}",
        "stream_url": f"/api/transcripts/stream/{job_id}",
    }
