"""Model lifecycle management — lazy loading, caching, cleanup."""
from __future__ import annotations

import gc
import logging
import os
import psutil                    # <-- ADD

import torch
from faster_whisper import WhisperModel   # <-- REPLACE openai-whisper

try:
    import huggingface_hub
    from huggingface_hub import file_download as hf_file_download
except Exception:  # pragma: no cover - optional runtime dependency edge
    huggingface_hub = None
    hf_file_download = None


def _patch_hf_hub_download_compat() -> None:
    """Map deprecated use_auth_token kwarg to token for pyannote compatibility."""
    if huggingface_hub is None:
        return

    original = huggingface_hub.hf_hub_download
    if getattr(original, "_transcription_compat_patch", False):
        return

    def _hf_hub_download_compat(*args, **kwargs):
        if "use_auth_token" in kwargs:
            legacy_token = kwargs.pop("use_auth_token")
            kwargs.setdefault("token", legacy_token)
        return original(*args, **kwargs)

    _hf_hub_download_compat._transcription_compat_patch = True  # type: ignore[attr-defined]
    huggingface_hub.hf_hub_download = _hf_hub_download_compat
    if hf_file_download is not None and hasattr(hf_file_download, "hf_hub_download"):
        hf_file_download.hf_hub_download = _hf_hub_download_compat


_patch_hf_hub_download_compat()

from pyannote.audio import Pipeline

logger = logging.getLogger(__name__)

_WHISPER_VARIANTS = {
    "tiny":     "tiny",
    "tiny.en":  "tiny.en",
    "base":     "base",
    "base.en":  "base.en",
    "small":    "small",
    "small.en": "small.en",
    "medium":   "medium",
    "medium.en":"medium.en",
    "large-v1": "large-v1",
    "large-v2": "large-v2",
    "large-v3": "large-v3",
    "turbo":    "turbo",
    "large":    "large-v3",       # alias
    "distil-large-v3": "distil-large-v3",
}

# Rough RAM estimates for int8 quantized faster-whisper on CPU (GiB)
_MODEL_RAM_ESTIMATES = {
    "tiny": 0.4, "tiny.en": 0.4,
    "base": 0.5, "base.en": 0.5,
    "small": 0.9, "small.en": 0.9,
    "medium": 2.0, "medium.en": 2.0,
    "large-v1": 2.4, "large-v2": 2.4, "large-v3": 2.4,
    "turbo": 1.8,
    "distil-large-v3": 1.6,
    "large": 2.4,
}




class ModelManager:
    """Manages heavy ML model instances (Whisper + Pyannote)."""

    def __init__(self):
        self._whisper_models: dict[str, WhisperModel] = {}
        self._diarization_pipeline: Pipeline | None = None

    def _available_ram_gib(self) -> float:
        """Return available system RAM in GiB."""
        return psutil.virtual_memory().available / (1024 ** 3)

    def _select_model(self, requested: str) -> str:
        """Pick the best model that fits in available RAM with 3 GiB headroom."""
        canonical = _WHISPER_VARIANTS.get(requested, "large-v3")
        available = self._available_ram_gib()
        needed = _MODEL_RAM_ESTIMATES.get(canonical, 2.4)
        headroom = 3.0  # keep 3 GiB for OS + other processes

        if available >= needed + headroom:
            return canonical

        # Walk down in size until one fits
        fallback_order = [
            "distil-large-v3", "turbo", "medium", "small", "base", "tiny"
        ]
        logger.warning(
            "[memory] only %.1f GiB available; %s needs ~%.1f GiB — trying fallbacks",
            available, canonical, needed,
        )

        for fb in fallback_order:
            fb_ram = _MODEL_RAM_ESTIMATES.get(fb, 0.9)
            if available >= fb_ram + headroom:
                logger.warning("[memory] falling back to '%s' (~%.1f GiB RAM needed)", fb, fb_ram)
                return fb

        # Last resort: use tiny
        logger.error("[memory] extreme low memory (%.1f GiB) — using 'tiny'", available)
        return "tiny"

    def get_whisper_model(self, model_size: str = "large-v3") -> WhisperModel:
        resolved = self._select_model(model_size)

        if resolved not in self._whisper_models:
            logger.info(
                "Loading Whisper model '%s' (available RAM: %.1f GiB)",
                resolved, self._available_ram_gib(),
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            self._whisper_models[resolved] = WhisperModel(
                resolved,
                device=device,
                compute_type=compute_type,
                cpu_threads=os.cpu_count() or 4,
                num_workers=1,
            )
        return self._whisper_models[resolved]


    def get_diarization_pipeline(self, token: str | None = None) -> Pipeline:
        if self._diarization_pipeline is None:
            logger.info("Loading Pyannote diarization pipeline")
            token = (
                token
                or os.getenv("PYANNOTE_AUTH_TOKEN")
                or os.getenv("HF_TOKEN")
                or os.getenv("HUGGINGFACE_HUB_TOKEN")
                or os.getenv("use_auth_token")
            )
            if not token:
                raise ValueError("Pyannote auth token missing.")

            # huggingface_hub >=1.0 removed use_auth_token from hf_hub_download.
            # Set HF_TOKEN in the environment so pyannote's internal hub calls
            # pick it up automatically — no deprecated kwarg, no network validation.
            os.environ["HF_TOKEN"] = token

            self._diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
            )
            try:
                if (
                    hasattr(self._diarization_pipeline, "segmentation")
                    and hasattr(self._diarization_pipeline.segmentation, "threshold")
                ):
                    self._diarization_pipeline.segmentation.threshold = 0.25
            except Exception:
                pass
        return self._diarization_pipeline

    def clear_cache(self):
        self._whisper_models = {}
        self._diarization_pipeline = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
