"""Model lifecycle management — lazy loading, caching, cleanup."""
from __future__ import annotations

import gc
import logging
import os

import torch
import whisper

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
from whisper import available_models

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages heavy ML model instances (Whisper + Pyannote)."""

    def __init__(self):
        self._whisper_models: dict[str, whisper.Whisper] = {}
        self._diarization_pipeline: Pipeline | None = None

    def get_whisper_model(self, model_size: str = "large-v3") -> whisper.Whisper:
        if model_size not in available_models():
            logger.warning(
                f"Model '{model_size}' not available. Falling back to 'large'. "
                f"Available: {available_models()}"
            )
            model_size = "large"
        if model_size not in self._whisper_models:
            logger.info(f"Loading Whisper model '{model_size}'")
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._whisper_models[model_size] = whisper.load_model(model_size, device=device)
        return self._whisper_models[model_size]

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
