"""transcription MCP server: health and model/parameter metadata tools.

Launch with:
    python -m src.mcp.servers.meta_server
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import torch
from mcp.server.fastmcp import FastMCP
from whisper import available_models

from src.config import settings

mcp = FastMCP("transcription-meta")


@mcp.tool()
def health() -> dict[str, Any]:
    """Return basic service health metadata."""
    return {
        "status": "ok",
        "service": "transcription",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@mcp.tool()
def health_full() -> dict[str, Any]:
    """Return extended runtime health metadata."""
    return {
        "status": "ok",
        "service": "transcription",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "torch_device": settings.TORCH_DEVICE,
        "torch_float": settings.TORCH_FLOAT,
        "cuda_available": torch.cuda.is_available(),
    }


@mcp.tool()
def list_parameter_definitions() -> dict[str, Any]:
    """Return full transcription parameter metadata."""
    return {
        "general": {
            "language": "Input language locale (maps to Whisper language code). Ex: es-CL, en, pt-BR.",
            "model_size": "Whisper model variant. Larger = better quality, slower & more RAM.",
            "min_speakers": "Lower bound for expected speakers (diarization constraint).",
            "max_speakers": "Upper bound for expected speakers (diarization constraint).",
            "vad_threshold": "Voice activity probability threshold (lower = more segments, higher = stricter).",
        },
        "preprocessing": {
            "noise_reduce": "Apply spectral noise reduction (slow for long audio).",
            "reduction_db": "Approximate aggressiveness (0-40). Higher may introduce artifacts.",
            "voice_enhance": "Apply band-pass filtering + dynamic range compression.",
            "apply_gain": "Loudness normalization toward target_lufs.",
            "target_lufs": "Target loudness (LUFS). Typical podcast: -16 (stereo) / -19 (mono).",
            "remove_silence": "Remove detected silence segments before diarization.",
            "silence_thresh": "Silence threshold dBFS (e.g. -45). Higher (less negative) removes more.",
            "min_silence_len": "Minimum silence length (ms) to qualify for removal.",
        },
        "whisper_decoding": {
            "beam_size": "Beam search width (larger = better accuracy, slower).",
            "best_of": "Number of sampled candidates when not using temperature=0.",
            "whisper_temp": "Starting sampling temperature. 0 = deterministic.",
            "temperature_increment_on_fallback": "Temperature added on each fallback attempt.",
            "compression_ratio_threshold": "Abort & retry if gzip ratio exceeds this.",
            "logprob_threshold": "Abort & retry if avg log-prob below this.",
            "no_speech_threshold": "If no-speech probability exceeds this -> treat as silence.",
            "condition_on_previous_text": "Feed previous segment text as context.",
            "initial_prompt": "Optional priming text or domain vocabulary.",
            "length_penalty": "Adjust preference for longer/shorter outputs in beam search.",
            "patience": "Beam search termination patience.",
            "suppress_blank": "Suppress blank tokens.",
            "suppress_tokens": "Comma list of token IDs to suppress (-1 = library default).",
            "word_timestamps": "Enable per-word timestamps (slower).",
        },
        "control": {
            "keep_cache": "Keep models in memory after request for reuse (faster subsequent calls).",
        },
    }


@mcp.tool()
def list_whisper_models() -> dict[str, Any]:
    """Return locally available Whisper model names."""
    return {"available_models": available_models()}


def main() -> None:
    """Entrypoint for stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
