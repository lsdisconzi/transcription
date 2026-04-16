"""DeepSeek transcript analyzer.

Implements TranscriptAnalyzerPort using DeepSeek's OpenAI-compatible API.
"""
from __future__ import annotations

import asyncio
import json
import logging

import openai

from src.domain.entities.transcript import Transcript

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a legal transcript analyst specializing in Chilean Spanish audio recordings.

Analyze the transcript and return a JSON object with these fields:
- "summary": A 2-4 sentence summary of the conversation in Spanish.
- "key_facts": A list of the most important factual claims or events mentioned.
- "entities": A list of objects {"name": str, "type": str} for people, places,
  organisations, dates, and legal references mentioned.
- "speakers": A list of objects {"label": str, "likely_role": str} guessing each
  speaker's role (e.g. "passenger", "police officer", "airline staff").
- "sentiment": Overall tone - one of "neutral", "confrontational", "cooperative",
  "distressed", "formal".
- "language_notes": Any notable Chilean Spanish expressions, slang, or dialect features.

Respond ONLY with valid JSON. No markdown fences, no commentary.
"""

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Approximate pricing in USD per million tokens for deepseek-chat.
_PRICE_INPUT_PER_M = 0.27
_PRICE_OUTPUT_PER_M = 1.10


class DeepSeekAnalyzerAdapter:
    """Analyze transcripts using DeepSeek chat models."""

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self._client = openai.OpenAI(api_key=api_key, base_url=_DEEPSEEK_BASE_URL)
        self._model = model

    async def analyze(
        self,
        transcript: Transcript,
        *,
        instructions: str = "",
    ) -> dict:
        text = "\n".join(
            f"[{seg.speaker.label}] ({seg.start:.1f}s - {seg.end:.1f}s): {seg.text}"
            for seg in transcript.segments
        )
        if not text.strip():
            return {"error": "Empty transcript - nothing to analyze."}

        user_prompt = f"Analyze this transcript:\n\n{text}"
        if instructions:
            user_prompt += f"\n\nAdditional instructions: {instructions}"

        response = await asyncio.to_thread(
            self._client.chat.completions.create,
            model=self._model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_text = (response.choices[0].message.content or "").strip()
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0

        try:
            analysis = json.loads(raw_text)
        except json.JSONDecodeError:
            analysis = {"raw_response": raw_text}

        analysis["_meta"] = {
            "model": self._model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": self._estimate_cost(tokens_in, tokens_out),
        }

        logger.info(
            "[deepseek-analyzer] transcript=%s tokens_in=%d tokens_out=%d",
            transcript.transcript_id,
            tokens_in,
            tokens_out,
        )
        return analysis

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        return round(
            (tokens_in * _PRICE_INPUT_PER_M + tokens_out * _PRICE_OUTPUT_PER_M) / 1_000_000,
            6,
        )
