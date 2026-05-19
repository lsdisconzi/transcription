"""Whisper ASR adapter — implements ASRPort."""
from __future__ import annotations

import logging

from src.infrastructure.model_manager import ModelManager

logger = logging.getLogger(__name__)


class WhisperASRAdapter:
    """Transcribes audio using faster-whisper. Implements ASRPort."""

    def __init__(self, model_manager: ModelManager):
        self._mm = model_manager

    def transcribe(
        self,
        audio_path: str,
        language: str = "es",
        **kwargs,
    ) -> str:
        model_size = kwargs.pop("model_size", "large-v3")
        model = self._mm.get_whisper_model(model_size)

        # ---- build transcription params, filtering out None values ----
        transcribe_kwargs: dict = {
            "language": language,
            "temperature": kwargs.get("temperature", 0.0),
            "beam_size": kwargs.get("beam_size", 5),
            "best_of": kwargs.get("best_of", 5),
            "compression_ratio_threshold": kwargs.get("compression_ratio_threshold", 2.4),
            "log_prob_threshold": kwargs.get("logprob_threshold", -1.0),
            "no_speech_threshold": kwargs.get("no_speech_threshold", 0.6),
            "condition_on_previous_text": kwargs.get("condition_on_previous_text", False),
            "length_penalty": kwargs.get("length_penalty", 1.0),
            "suppress_blank": kwargs.get("suppress_blank", True),
            "suppress_tokens": kwargs.get("suppress_tokens", [-1]),
            "word_timestamps": kwargs.get("word_timestamps", False),
            "vad_filter": False,
        }

        # Optional params — only add if non-None
        if kwargs.get("initial_prompt"):
            transcribe_kwargs["initial_prompt"] = kwargs["initial_prompt"]
        if kwargs.get("patience") is not None:
            transcribe_kwargs["patience"] = kwargs["patience"]

        segments, _info = model.transcribe(audio_path, **transcribe_kwargs)

        results = list(segments)
        if not results:
            return ""
        return "".join(seg.text for seg in results)

    def clear_cache(self):
        self._mm.clear_cache()