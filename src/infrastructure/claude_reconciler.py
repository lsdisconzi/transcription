"""Claude-powered transcript reconciliation.

Implements TranscriptReconcilerPort. Takes raw Whisper output + reference
transcript and produces a reconciled result with named speakers, corrected
text, and confidence annotations.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math

import anthropic

from src.domain.entities.reference import IncidentNarrative, ReferenceTranscript

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a transcript reconciliation specialist for Chilean Spanish audio recordings.

You receive up to three inputs:
1. RAW — a new transcription from Whisper with generic speaker labels (SPEAKER_00, etc.)
2. REFERENCE — a previously corrected transcript of the SAME audio with named speakers
3. NARRATIVE (optional) — a first-person chronological account of events during this audio, \
written by the passenger. Contains timestamped descriptions, named individuals, and exact \
quotes that describe what was happening at each moment.

Your task:
1. MAP speakers: Match SPEAKER_00/01/02 to named roles (passenger, airline_staff, \
police_officer, etc.) by comparing what each speaker says in RAW against the REFERENCE \
and NARRATIVE. The narrative identifies real names and roles.
2. CORRECT text: Fix obvious Whisper errors using the REFERENCE and NARRATIVE as ground \
truth. Whisper often hallucinates repetitions, drops words, or misrecognizes names.
3. PRESERVE novelty: If the RAW transcript contains valid content NOT in the REFERENCE, \
keep it — the reference may be incomplete.
4. KEEP timing: Use start/end times from the RAW transcript (they come from this run). \
Reference timing may differ due to different preprocessing.
5. FLAG disagreements: When RAW and REFERENCE significantly disagree on a segment, \
add "confidence": 0.5 and "flag": "disagree" to that segment.
6. MAINTAIN dialect: Keep Chilean Spanish as-is. Do NOT "correct" dialect to standard \
Spanish. Terms like "cachai", "po", "wea" are correct.
7. USE NARRATIVE for context: The narrative provides situational context — who is speaking, \
what they are reacting to, what is happening in the background. Use this to resolve \
ambiguous segments and correctly attribute speakers.

Output ONLY a JSON object with this exact structure:
{
  "speaker_map": {"SPEAKER_00": "passenger", "SPEAKER_01": "airline_staff"},
  "segments": [
    {
      "id": "0",
      "speaker": "passenger",
      "start": 0.03,
      "end": 20.69,
      "text": "...",
      "language": "es",
      "confidence": 0.9
    }
  ],
  "reconciliation_notes": "Brief summary of changes made"
}

No markdown fences. No commentary outside the JSON."""

# Process segments in batches to stay within token limits
_BATCH_SIZE = 30
_MAX_REFERENCE_CONTEXT_TOKENS = 3000


class ClaudeReconcilerAdapter:
    """Reconcile transcripts using Anthropic Claude. Implements TranscriptReconcilerPort."""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-v4-pro",
        base_url: str = "https://api.deepseek.com/anthropic",
    ):
        self._client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self._model = model

    async def reconcile(
        self,
        raw_segments: list[dict],
        reference: ReferenceTranscript,
        *,
        narrative: IncidentNarrative | None = None,
        language: str = "es",
    ) -> dict:
        if not raw_segments:
            return {"segments": [], "speaker_map": {}, "reconciliation_notes": "Empty input"}

        # Build reference context (truncated to budget)
        ref_context = self._build_reference_context(reference)

        # Build narrative context if available
        narrative_context = self._build_narrative_context(narrative) if narrative else ""

        # Process in batches if needed
        all_reconciled: list[dict] = []
        total_tokens_in = 0
        total_tokens_out = 0
        speaker_map: dict[str, str] = {}
        notes_parts: list[str] = []

        num_batches = math.ceil(len(raw_segments) / _BATCH_SIZE)
        for batch_idx in range(num_batches):
            start = batch_idx * _BATCH_SIZE
            end = min(start + _BATCH_SIZE, len(raw_segments))
            batch = raw_segments[start:end]

            # Find overlapping reference segments by time range
            batch_start_time = batch[0].get("start", 0)
            batch_end_time = batch[-1].get("end", 0)
            ref_overlap = self._find_overlapping_reference_segments(
                reference, batch_start_time, batch_end_time
            )

            result = await self._reconcile_batch(
                batch, ref_overlap, ref_context, narrative_context,
                language, batch_idx + 1, num_batches,
            )

            all_reconciled.extend(result.get("segments", []))
            total_tokens_in += result.get("_tokens_in", 0)
            total_tokens_out += result.get("_tokens_out", 0)

            # Merge speaker maps (first batch establishes the mapping)
            batch_map = result.get("speaker_map", {})
            if batch_map:
                speaker_map.update(batch_map)

            if result.get("reconciliation_notes"):
                notes_parts.append(result["reconciliation_notes"])

        cost = self._estimate_cost(total_tokens_in, total_tokens_out)
        logger.info(
            "[reconciler] %d raw → %d reconciled, tokens_in=%d tokens_out=%d cost=$%.4f",
            len(raw_segments),
            len(all_reconciled),
            total_tokens_in,
            total_tokens_out,
            cost,
        )

        return {
            "segments": all_reconciled,
            "speaker_map": speaker_map,
            "reconciliation_notes": " | ".join(notes_parts),
            "participants": list(set(speaker_map.values())),
            "_meta": {
                "model": self._model,
                "tokens_in": total_tokens_in,
                "tokens_out": total_tokens_out,
                "cost_usd": cost,
                "batches": num_batches,
                "reference_used": reference.title,
            },
        }

    async def _reconcile_batch(
        self,
        raw_batch: list[dict],
        ref_segments: list[dict],
        ref_context: str,
        narrative_context: str,
        language: str,
        batch_num: int,
        total_batches: int,
    ) -> dict:
        raw_text = json.dumps(raw_batch, ensure_ascii=False)
        ref_text = json.dumps(ref_segments, ensure_ascii=False)

        user_prompt = (
            f"Batch {batch_num}/{total_batches}. Language: {language}\n\n"
            f"REFERENCE CONTEXT:\n{ref_context}\n\n"
            f"REFERENCE SEGMENTS (time-overlapping):\n{ref_text}\n\n"
        )
        if narrative_context:
            user_prompt += f"INCIDENT NARRATIVE (passenger account):\n{narrative_context}\n\n"
        user_prompt += f"RAW WHISPER OUTPUT:\n{raw_text}"

        response = await asyncio.to_thread(
            self._client.messages.create,
            model=self._model,
            max_tokens=8192,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_response = response.content[0].text
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.warning("[reconciler] batch %d: invalid JSON response", batch_num)
            result = {
                "segments": raw_batch,
                "speaker_map": {},
                "reconciliation_notes": "LLM returned invalid JSON — using raw segments",
            }

        result["_tokens_in"] = tokens_in
        result["_tokens_out"] = tokens_out
        return result

    def _build_reference_context(self, reference: ReferenceTranscript) -> str:
        """Build a compact context string from reference metadata."""
        parts = [
            f"Audio: {reference.title}",
            f"Participants: {', '.join(reference.participants)}",
            f"Language: {reference.language}",
        ]
        if reference.location:
            parts.append(f"Location: {reference.location}")
        if reference.recording_datetime:
            parts.append(f"Date: {reference.recording_datetime}")
        return "\n".join(parts)

    def _build_narrative_context(
        self, narrative: IncidentNarrative, max_chars: int = 4000
    ) -> str:
        """Extract the relevant portion of a narrative for reconciliation context.

        Narratives contain timestamped chronological accounts. We include the
        full text up to max_chars — the narrative provides crucial context about
        who is present, what they are doing, and the situational background.
        """
        text = narrative.text.strip()
        if len(text) <= max_chars:
            return text
        # Truncate at a paragraph boundary
        truncated = text[:max_chars]
        last_break = truncated.rfind("\n\n")
        if last_break > max_chars // 2:
            truncated = truncated[:last_break]
        return truncated + "\n[... narrative truncated ...]"

    def _find_overlapping_reference_segments(
        self,
        reference: ReferenceTranscript,
        start_time: float,
        end_time: float,
        margin: float = 5.0,
    ) -> list[dict]:
        """Find reference segments that overlap the given time range."""
        result = []
        for seg in reference.content:
            if seg.end >= (start_time - margin) and seg.start <= (end_time + margin):
                result.append({
                    "id": seg.id,
                    "speaker": seg.speaker,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "language": seg.language,
                    "confidence": seg.confidence,
                })
        return result

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost based on Sonnet pricing ($3/M in, $15/M out)."""
        return round((tokens_in * 3 + tokens_out * 15) / 1_000_000, 6)
