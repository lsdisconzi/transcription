"""Claude transcript analyzer — implements TranscriptAnalyzerPort."""
from __future__ import annotations

import logging

import anthropic

from src.domain.entities.transcript import Transcript

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a legal transcript analyst specializing in Chilean Spanish audio recordings.

Analyze the transcript and return a JSON object with these fields:
- "summary": A 2-4 sentence summary of the conversation in Spanish.
- "key_facts": A list of the most important factual claims or events mentioned.
- "entities": A list of objects {"name": str, "type": str} for people, places, \
organisations, dates, and legal references mentioned.
- "speakers": A list of objects {"label": str, "likely_role": str} guessing each \
speaker's role (e.g. "passenger", "police officer", "airline staff").
- "sentiment": Overall tone — one of "neutral", "confrontational", "cooperative", \
"distressed", "formal".
- "language_notes": Any notable Chilean Spanish expressions, slang, or dialect features.

Respond ONLY with valid JSON. No markdown fences, no commentary."""


class ClaudeAnalyzerAdapter:
    """Analyze transcripts using Anthropic Claude. Implements TranscriptAnalyzerPort."""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-v4-pro",
        base_url: str = "https://api.deepseek.com/anthropic",
    ):
        self._client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self._model = model

    async def analyze(
        self,
        transcript: Transcript,
        *,
        instructions: str = "",
    ) -> dict:
        text = "\n".join(
            f"[{seg.speaker.label}] ({seg.start:.1f}s – {seg.end:.1f}s): {seg.text}"
            for seg in transcript.segments
        )
        if not text.strip():
            return {"error": "Empty transcript — nothing to analyze."}

        user_prompt = f"Analyze this transcript:\n\n{text}"
        if instructions:
            user_prompt += f"\n\nAdditional instructions: {instructions}"

        import asyncio

        response = await asyncio.to_thread(
            self._client.messages.create,
            model=self._model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        # Parse JSON response
        import json

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
            "[claude] analyzed transcript=%s tokens_in=%d tokens_out=%d",
            transcript.transcript_id,
            tokens_in,
            tokens_out,
        )
        return analysis

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost based on Sonnet pricing ($3/M in, $15/M out)."""
        return round((tokens_in * 3 + tokens_out * 15) / 1_000_000, 6)
