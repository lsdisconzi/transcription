User: @/Users/leandrodisconzi/Downloads/aeropuerto_STG_20_segment_1.json @/Users/leandrodisconzi/Downloads/aeropuerto_STG_20.json @/Users/leandrodisconzi/Downloads/incident_narrative_aeropuerto_STG_20_2024-07-05T19-46-00.000Z.txt @/Users/leandrodisconzi/Downloads/README (1).md All right, so how can we, right, how can we use the transcription services functionalities, be it internal, be it using any of the other services that we have access to locally, how could we use these files, for example, right, to then configure it properly, Pinocchio, to make a good transcription and diarization? And also link or use the audio project, which we have the MCP tools for it also, to be able to manipulate the audio. So ideally, it would be nice to have what in Pinocchio. If it is local or a PyAnote, right, we could start by a interaction with the agent and say, look, have a preview, listen to this audio. These are the transcripts that we have made. This is like the narrative. Try to listen to it and analyze it, see if maybe it could benefit from some audio modification, manipulation processing, right? And then it could use the all internal pre-processing, but also the audio project processing capabilities, which are higher, right? And then it could check back and so on, right? How could we use that to really not redo everything, but only analyze and, you know, validate and maybe get a few things more correct than what it is.

Claude: Read [](file:///Users/leandrodisconzi/Downloads/README%20%281%29.md)

Ran terminal command: ls /Users/dev/services/transcription && echo "---" && ls /Users/leandrodisconzi/work/audio-processing/audio 2>/dev/null | head -40

Read [](file:///Users/dev/services/transcription/README.md)

Read [](file:///Users/leandrodisconzi/work/audio-processing/audio/README.md)

Ran terminal command: ls /Users/dev/services/transcription/src/application/use_cases 2>/dev/null && echo "---infra---" && ls /Users/dev/services/transcription/src/infrastructure 2>/dev/null && echo "---mcp---" && ls /Users/dev/services/transcription/src/mcp/servers 2>/dev/null

Ran terminal command: wc -l /Users/dev/services/transcription/src/application/use_cases/guided_transcribe.py /Users/dev/services/transcription/src/infrastructure/pydub_processor.py /Users/dev/services/transcription/src/infrastructure/claude_reconciler.py 2>/dev/null && echo "---audio repo top---" && ls /Users/leandrodisconzi/work/audio-processing/audio/mcp 2>/dev/null && echo "---" && ls /Users/leandrodisconzi/work/audio-processing/audio/src 2>/dev/null | head -30

Ran terminal command: ls /Users/leandrodisconzi/work/audio-processing/audio/mcp/torchaudio_mcp 2>/dev/null && echo "---tools---" && ls /Users/leandrodisconzi/work/audio-processing/audio/mcp/torchaudio_mcp/tools 2>/dev/null 2>&1 | head -40

Ran terminal command: grep -E "^(def |async def |@app\.|@mcp\.|tool\()" /Users/leandrodisconzi/work/audio-processing/audio/mcp/torchaudio_mcp/server.py 2>/dev/null | head -60

Ran terminal command: grep -nE "^(def |class |async def )" /Users/dev/services/transcription/src/application/use_cases/guided_transcribe.py /Users/dev/services/transcription/src/infrastructure/claude_reconciler.py /Users/dev/services/transcription/src/infrastructure/pydub_processor.py 2>/dev/null

Read [](file:///Users/dev/services/transcription/src/application/use_cases/guided_transcribe.py)

You already have most of the bones for this exact workflow — `ReferenceGuidedTranscribeUseCase` ([src/application/use_cases/guided_transcribe.py](src/application/use_cases/guided_transcribe.py)) is the "use the existing transcript + narrative as a prior, re-run ASR/diarization, then reconcile with an LLM" loop. The missing piece is wiring the audio MCP in as a **second-tier preprocessor + acoustic-evidence tool** the agent can call when the cheap path isn't enough.

## What the inputs reveal

Reading `aeropuerto_STG_20.json` next to the narrative, the transcript has acoustic signs the audio could fix — not text fixes:
- **Duplicate IDs** ("7" appears twice, "9" twice) — pyannote split a single utterance across two windows.
- **Mid-word cut**: id 8 `"Una de agresión."` → id 9 `" ¿Nadie te "` → id "7" `"acusó por agressión?"` is one sentence shattered into 3 segments by overlap/silence.
- **Long gaps** (13.53→17.5, 42.86→52.97) — silence or shouting muffled below the VAD threshold.
- **Speaker label drift**: `Joaquin Barraa` (segment_1) vs `Joaquin Barraza` (full) — the same person, different runs.
- **`agressión`** — Portuguese-influenced spelling; Whisper drift on Chilean Spanish.

## Recommended loop (agent-driven, no full re-run)

1. **Audit pass** — agent calls `transcription_audio_info` (audio MCP) for SR, channels, peak/RMS; `list_transcripts` + `get_transcript` to load the existing JSON; reads the narrative. From this it produces a *delta plan*: "segments 7–9 likely one utterance; check 25–28s loudness; speaker map needs canonicalization."

2. **Targeted acoustic probes** — only on flagged windows:
   - `transcription_extract_features` over 38–43s → spectrogram/MFCC tells you whether the gap is silence, crosstalk, or clipping.
   - `diarize_excerpt` (already exists in the transcription MCP) on just 36–44s with `min_speakers=2, max_speakers=2` to settle the split.

3. **Conditional reprocessing** — if probes show low SNR or clipping, route the *clip* (not the whole file) through the audio MCP for higher-grade preprocessing (torchaudio resample/denoise/normalize) — that's the tier above your `PydubProcessorAdapter`. Save the cleaned excerpt, re-diarize/re-ASR just that clip with the **narrative as `initial_prompt`**.

4. **Reconciliation** — feed (original segments, new excerpt segments, narrative, reference transcript) to `ClaudeReconcilerAdapter`. Already does this; you'd just give it explicit "patch these IDs" guidance. Output: a *patched* transcript, not a redone one.

5. **Validation** — agent re-reads the patched JSON, checks ID uniqueness/timeline monotonicity, and confirms speaker-label consistency against the canonical name in the reference store.

## Where to put it

A new use case `validate_and_refine_transcript.py` next to `guided_transcribe.py`, taking `(transcript_id, narrative_id?)` and orchestrating the steps above. It reuses every existing port — only the audio-MCP calls are new, exposed through an `AcousticProbePort` so the production code doesn't depend on the MCP transport.

## Main tradeoff

Cheap-and-textual (just re-run reconciler with the narrative as a prior) catches most ID/spelling issues without touching audio. Audio-aware refinement catches the *real* diarization splits but costs a torchaudio round-trip per flagged window. Default to text-only; let the agent escalate to acoustic probes only when it flags structural anomalies (duplicate IDs, time gaps > N seconds, mid-word boundaries) — that's the "not redo everything, only validate" behavior you described.

Want me to sketch the `validate_and_refine_transcript` use case + the `AcousticProbePort` interface as a concrete plan before any code goes in?

User: sure, go ahead with your suggestion

Claude: Ran terminal command: ls /Users/dev/services/transcription/src/domain/ports /Users/dev/services/transcription/src/domain/entities 2>/dev/null && echo "---composition---" && ls /Users/dev/services/transcription/src/composition.py 2>/dev/null && wc -l /Users/dev/services/transcription/src/composition.py /Users/dev/services/transcription/src/domain/ports/interfaces.py /Users/dev/services/transcription/src/mcp/servers/transcripts_server.py /Users/dev/services/transcription/src/application/use_cases/diarize_excerpt.py 2>/dev/null

Read [](file:///Users/dev/services/transcription/src/domain/ports/interfaces.py)

Read [](file:///Users/dev/services/transcription/src/composition.py)

Read [](file:///Users/dev/services/transcription/src/application/use_cases/diarize_excerpt.py)

Read [](file:///Users/dev/services/transcription/src/mcp/servers/transcripts_server.py)

Read [](file:///Users/dev/services/transcription/src/infrastructure/claude_reconciler.py)

Ran terminal command: grep -nE "^(class |    def |    [a-z_]+:)" /Users/dev/services/transcription/src/domain/entities/transcript.py 2>/dev/null | head -40 && echo "---audio mcp signatures---" && grep -nA 6 "^@mcp.tool" /Users/leandrodisconzi/work/audio-processing/audio/mcp/torchaudio_mcp/server.py | head -90

Here is the plan. No code yet — review and tell me what to adjust.

## Architecture decision: agent-driven, not service-to-service

The audio project already exposes an MCP server (torchaudio_mcp). The cleanest pattern is **a single agent connected to both MCPs** — it audits, decides which acoustic probes to run, and patches. The transcription service does NOT call the audio MCP itself; instead it grows three concerns:

1. A pure-domain **auditor** that flags structural issues in a stored transcript.
2. A **port** (`AcousticProbePort`) so the same logic can also run automatically — the adapter behind it can either shell out to torchaudio in-process or wrap an MCP client. Default ships in-process.
3. New **MCP tools** that expose audit + window-level patch ops to the agent.

This way the user's described loop ("agent listens, validates, asks audio MCP for help") runs through Claude as the orchestrator, while the transcription service stays usable headless.

## Files to add

| Path | Purpose |
|---|---|
| `src/domain/entities/anomaly.py` | `Anomaly(kind, segment_ids, start, end, severity, hint)` — small dataclass |
| `src/domain/ports/interfaces.py` (extend) | New `AcousticProbePort` Protocol |
| `src/application/services/transcript_auditor.py` | Pure auditor — no I/O, takes `Transcript`, returns `list[Anomaly]` |
| `src/application/use_cases/validate_and_refine_transcript.py` | Orchestration use case |
| `src/infrastructure/torchaudio_probe_adapter.py` | Implements `AcousticProbePort` using torchaudio directly (in-process) |
| `tests/application/test_transcript_auditor.py` | Unit tests with fixture transcripts (incl. the STG_20 case) |
| `tests/application/test_validate_and_refine_transcript.py` | Use-case tests with fakes |

Files to modify: `src/composition.py` (wire the new use case), `src/mcp/servers/transcripts_server.py` (add 3 tools).

## 1. `AcousticProbePort` (new Protocol)

```
audio_info(path) -> {sample_rate, channels, duration, peak_db, rms_db, clipping_pct}
window_stats(path, start, end) -> {rms_db, snr_estimate, silence_ratio, voiced_ratio}
extract_window(src_path, start, end, dst_path) -> str   # writes a clip
```

Three methods only — anything fancier (spectrograms, MFCCs) belongs to the agent's call into the audio MCP, not to our port. Keeps the port narrow.

## 2. `TranscriptAuditor` rules (pure)

Run in this order; each produces zero or more `Anomaly`:

| Rule | Severity | Detection |
|---|---|---|
| **DuplicateIds** | high | `seg.index` (or `id`) collides — STG_20 has IDs "7" and "9" twice |
| **MidWordBoundary** | high | Adjacent same-speaker segments where the first ends without sentence-final punctuation AND the second starts with a lowercase letter or `¿`/`¡`. STG_20: id 8→9→7 around 38–43s |
| **TimeGap** | medium | Gap between `seg.end` and `seg[i+1].start` ≥ `gap_threshold_s` (default 4.0) |
| **MicroSegment** | low | `duration < 0.5s` and ends without punctuation — typical pyannote leakage |
| **SpeakerLabelDrift** | medium | Label appears < min_occurrences AND fuzzy-matches another label (Levenshtein ≤ 2). STG_20: `Joaquin Barraa` vs `Joaquin Barraza` |
| **NonMonotonicTimes** | high | `seg[i+1].start < seg[i].start` |

Output: `AuditReport(transcript_id, anomalies, summary_counts)`. Pure functions, fully testable without audio.

## 3. `ValidateAndRefineTranscriptUseCase`

```
execute(
    transcript_id: str,
    *,
    canonical_name: str | None = None,    # for ref/narrative lookup
    use_acoustic_probes: bool = False,    # gate the second tier
    apply_patches: bool = True,
    max_windows: int = 8,                 # budget guard
) -> ValidateAndRefineResult
```

Pipeline:

1. Load transcript via `TranscriptStorePort`.
2. Run `TranscriptAuditor` → anomalies.
3. **Cheap path** (always): for `DuplicateIds`, `MicroSegment`, `SpeakerLabelDrift`, `NonMonotonicTimes` — fix deterministically (renumber, merge, canonicalize labels). No LLM, no audio.
4. **Reconciler path** (if reconciler + reference exist): for `MidWordBoundary` and `TimeGap` flagged windows, send only those segments + narrative slice + reference slice to `TranscriptReconcilerPort`. Reuse the existing reconciler — no new prompt logic.
5. **Acoustic path** (only if `use_acoustic_probes=True`): for windows still flagged after step 4, call `AcousticProbePort.window_stats`. If `silence_ratio > 0.6` → drop the window. If `snr_estimate < threshold` → extract clip, run `processor.process` on the clip, then re-diarize via `diarizer.diarize` on the clip with `min_speakers=2,max_speakers=2`, splice results back. This is the "escalation" tier and is opt-in.
6. Re-run auditor on the patched transcript; persist; return audit-before/audit-after + diff.

Result shape:

```
{
  transcript_id, anomalies_before, anomalies_after,
  patches_applied: [{kind, segment_ids, action}],
  acoustic_probes_run: int,
  reconciler_calls: int,
  cost_usd: float,
}
```

## 4. New MCP tools on `transcripts_server`

| Tool | What it returns | Why |
|---|---|---|
| `audit_transcript(transcript_id)` | `AuditReport` JSON | Lets the agent decide whether to escalate |
| `validate_and_refine_transcript(transcript_id, canonical_name?, use_acoustic_probes=False, apply_patches=True)` | Result above | Headless one-shot |
| `patch_transcript_segments(transcript_id, patches: list[Patch])` | New transcript_id | Lets the agent (after listening with audio MCP) hand back hand-crafted edits |

Where `Patch` is `{op: "replace"|"merge"|"split"|"relabel", segment_ids: [...], new_text?, new_speaker?, new_start?, new_end?}`.

The agent loop the user described is then literally:
1. `audit_transcript("aeropuerto_STG_20")` → sees DuplicateIds + MidWordBoundary at 38–43s.
2. Agent decides those windows look acoustically suspicious → calls `transcription_audio_info` and `transcription_extract_features` on the audio MCP for 38–43s.
3. Based on what it sees, either calls `validate_and_refine_transcript(..., use_acoustic_probes=True)` to let the service do it, or hand-crafts `patch_transcript_segments(...)`.
4. Re-runs `audit_transcript` to confirm clean.

## 5. Composition wiring

In `composition.py`, build `TorchaudioProbeAdapter` once; gate it on a new `ENABLE_ACOUSTIC_PROBES` setting (defaults off — torchaudio is heavy and not everyone has it). Pass into the new use case. Use case treats `AcousticProbePort | None` and skips step 5 when None.

## 6. Testing

The STG_20 transcript you pasted is the perfect fixture. Save a sanitized copy in `tests/fixtures/aeropuerto_STG_20.json`; assert the auditor flags exactly: duplicate id "7", duplicate id "9", mid-word boundary at segments 8/9, time gaps at 13.53→17.5 and 42.86→52.97, speaker drift "Joaquin Barraa"↔"Joaquin Barraza" (cross-fixture). Then assert the use case (with reconciler stubbed) produces a transcript with unique IDs and merged segment 8/9 — without touching audio.

## Tradeoff to flag now

Steps 3 (deterministic) and 4 (reconciler) are the 80% case and need no audio at all. Step 5 (acoustic) is the only piece that pulls torchaudio into this service. If you'd rather keep this service lean, we can skip the `AcousticProbePort` adapter entirely and rely on the agent calling the audio MCP itself — the use case stays useful for the cheap path, and the agent does escalation. My default recommendation is to ship steps 1–4 first, leave the port + adapter as a stub, and only fill it in once we see how often the cheap path is insufficient.

Want me to (a) start implementing steps 1–4 (auditor + use case + MCP tools, no torchaudio), or (b) include the `AcousticProbePort` + in-process torchaudio adapter from day one?

User: define the whole development strategy and details (great by the way) with option B, then we will pass it to the agents in the project to implement

Claude: Read [](file:///Users/dev/services/transcription/src/domain/entities/transcript.py)

Read [](file:///Users/dev/services/transcription/src/domain/entities/reference.py)

Read [](file:///Users/dev/services/transcription/src/infrastructure/pydub_processor.py)

Ran terminal command: grep -n "REFERENCE_DIR\|NARRATIVE_DIR\|AUDIO_DIR\|ORIGINALS_DIR\|REFERENCE_AUDIO\|class Settings" /Users/dev/services/transcription/src/config.py 2>/dev/null | head -20 && echo "---ref store load_references---" && grep -nA 12 "def load_references\|def load_manifest" /Users/dev/services/transcription/src/infrastructure/reference_store_adapter.py 2>/dev/null | head -50

# Development strategy — `validate-and-refine-transcript`

Hand-off document. Every section below is a self-contained work package an agent can pick up. WP1→WP7 must ship in order; WP3 + WP4 can run in parallel after WP2 lands.

---

## 0. Goal & non-goals

**Goal.** Add an audit + targeted-refinement loop on top of stored transcripts so an agent (or the service headlessly) can validate an existing transcript and patch only the broken windows — without rerunning ASR or diarization on the whole file. Use torchaudio in-process for acoustic probes; reuse the existing reconciler for textual fixes.

**Non-goals.**
- No changes to existing use cases (`TranscribeAudioUseCase`, `ReferenceGuidedTranscribeUseCase`, `DiarizeExcerptUseCase`).
- No new LLM prompt — reuse `ClaudeReconcilerAdapter` / `DeepSeekReconcilerAdapter` as-is.
- No HTTP/FastAPI endpoint in this batch (MCP only). HTTP can come later.
- No Qdrant re-indexing in the use case itself; the agent re-runs `index_transcript` separately if it wants.

**Success criteria.**
1. Given the `aeropuerto_STG_20.json` fixture, the auditor flags exactly the anomalies listed in §6.1 with no false positives.
2. The use case fixes deterministic anomalies (duplicate IDs, label drift, micro-segments, non-monotonic times) with zero LLM calls.
3. With the reconciler enabled, mid-word boundaries and time gaps in the fixture are reduced to zero.
4. With `use_acoustic_probes=True`, the use case routes flagged windows through `AcousticProbePort.window_stats`, decides escalate vs. drop, and persists a patched transcript whose audit-after report has lower or equal severity than audit-before for every category.
5. Three new MCP tools are reachable from the transcripts server. Smoke test in `tests/mcp/test_validate_refine_mcp.py` passes.

---

## 1. Architecture overview

```
        ┌──────────────────────── presentation ────────────────────────┐
        │  src/mcp/servers/transcripts_server.py                       │
        │    + audit_transcript                                        │
        │    + validate_and_refine_transcript                          │
        │    + patch_transcript_segments                               │
        └────────────────────────┬─────────────────────────────────────┘
                                 │
        ┌────────────────────── application ───────────────────────────┐
        │ services/transcript_auditor.py        (pure)                 │
        │ services/transcript_patcher.py        (pure)                 │
        │ use_cases/validate_and_refine_transcript.py                  │
        └────────────────────────┬─────────────────────────────────────┘
                                 │
        ┌──────────────────────── domain ──────────────────────────────┐
        │ entities/anomaly.py                                          │
        │ entities/patch.py                                            │
        │ ports/interfaces.py                                          │
        │   + AcousticProbePort                                        │
        └────────────────────────┬─────────────────────────────────────┘
                                 │
        ┌────────────────────── infrastructure ────────────────────────┐
        │ torchaudio_probe_adapter.py  → AcousticProbePort             │
        │   uses torchaudio.load / functional / transforms             │
        │   uses src.infrastructure.audio_file_adapter for clip writes │
        └──────────────────────────────────────────────────────────────┘
```

Composition root (`src/composition.py`) wires the new adapter once, gated by `ENABLE_ACOUSTIC_PROBES`. The use case takes the port as `AcousticProbePort | None` and skips acoustic escalation when None — that keeps boot working on machines where torchaudio fails to import.

---

## 2. WP1 — Domain entities

**Files**

- `src/domain/entities/anomaly.py` (new)
- `src/domain/entities/patch.py` (new)
- `src/domain/entities/__init__.py` (export both)

**`anomaly.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class AnomalyKind(str, Enum):
    DUPLICATE_IDS = "duplicate_ids"
    MID_WORD_BOUNDARY = "mid_word_boundary"
    TIME_GAP = "time_gap"
    MICRO_SEGMENT = "micro_segment"
    SPEAKER_LABEL_DRIFT = "speaker_label_drift"
    NON_MONOTONIC_TIMES = "non_monotonic_times"

class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass(frozen=True)
class Anomaly:
    kind: AnomalyKind
    severity: Severity
    segment_indices: tuple[int, ...]   # internal `index` field, not the JSON id
    start: float
    end: float
    hint: str                          # one-line human-readable; goes into MCP tool output
    detail: dict = None                # free-form for kind-specific data (e.g. cluster of drifting labels)

@dataclass(frozen=True)
class AuditReport:
    transcript_id: str
    anomalies: tuple[Anomaly, ...]
    counts_by_kind: dict[str, int]
    counts_by_severity: dict[str, int]
```

**`patch.py`**

```python
class PatchOp(str, Enum):
    REPLACE_TEXT = "replace_text"
    MERGE = "merge"
    SPLIT = "split"
    RELABEL = "relabel"
    RETIME = "retime"
    DELETE = "delete"
    INSERT = "insert"

@dataclass(frozen=True)
class Patch:
    op: PatchOp
    segment_indices: tuple[int, ...]   # which segments are affected
    new_text: str | None = None
    new_speaker: str | None = None
    new_start: float | None = None
    new_end: float | None = None
    insert_after_index: int | None = None
    note: str = ""
```

Validation belongs to the patcher (WP4), not the dataclass.

**Acceptance.** Module imports cleanly. No external deps. Unit test asserts `Anomaly` is hashable and frozen.

---

## 3. WP2 — `AcousticProbePort` and tests double

**Files**

- `src/domain/ports/interfaces.py` (extend)
- `tests/_fakes/fake_acoustic_probe.py` (new)

**Port**

```python
@runtime_checkable
class AcousticProbePort(Protocol):
    """Acoustic measurement and clip extraction. Lightweight numerical probes only —
    no ASR, no diarization. Implementations may use torchaudio, soundfile, etc."""

    def audio_info(self, path: str) -> dict:
        """Return: {sample_rate:int, channels:int, duration:float,
                    peak_db:float, rms_db:float, clipping_pct:float}"""
        ...

    def window_stats(self, path: str, start: float, end: float) -> dict:
        """Return: {duration:float, rms_db:float, peak_db:float,
                    silence_ratio:float, voiced_ratio:float, snr_estimate:float}.

        silence_ratio: fraction of frames below -50 dBFS.
        voiced_ratio: fraction of frames whose spectral flatness < 0.4 (heuristic).
        snr_estimate: peak_db - noise_floor_db where noise_floor is the 10th-percentile
                      frame RMS in the window."""
        ...

    def extract_window(
        self, src_path: str, start: float, end: float, dst_path: str
    ) -> str:
        """Write [start,end] of src as 16 kHz mono WAV to dst_path. Return dst_path."""
        ...
```

**Fake** for testing — accepts a dict of canned responses keyed by `(path, start, end)` tuple, raises `KeyError` if asked something it wasn't preset with. Force tests to be explicit about probe inputs.

**Acceptance.** Port is importable, fake is used by the WP6 use-case tests.

---

## 4. WP3 — `TorchaudioProbeAdapter` (in-process)

**File**

- `src/infrastructure/torchaudio_probe_adapter.py` (new)

**Dependencies.** Add to `requirements.txt`:
- `torch>=2.4`
- `torchaudio>=2.4`
- `soundfile>=0.12`  (resampling fallback if torchaudio backend missing)

Confirm versions match the torchaudio fork at `/Users/leandrodisconzi/work/audio-processing/audio` — this adapter does NOT depend on the fork; it uses upstream torchaudio. If the user wants to pin to the fork, that's a follow-up.

**Implementation guidance**

```python
class TorchaudioProbeAdapter:
    """In-process AcousticProbePort using torchaudio."""

    def __init__(self, target_sample_rate: int = 16000):
        self._target_sr = target_sample_rate

    def audio_info(self, path: str) -> dict:
        info = torchaudio.info(path)
        wav, sr = torchaudio.load(path)            # (channels, frames)
        mono = wav.mean(dim=0)
        peak = mono.abs().max().item()
        rms = mono.pow(2).mean().sqrt().item()
        clipping = (mono.abs() >= 0.999).float().mean().item()
        return {
            "sample_rate": info.sample_rate,
            "channels": info.num_channels,
            "duration": info.num_frames / info.sample_rate,
            "peak_db": _linear_to_db(peak),
            "rms_db": _linear_to_db(rms),
            "clipping_pct": clipping * 100.0,
        }

    def window_stats(self, path, start, end):
        # frame-offset slice via torchaudio.load(frame_offset=, num_frames=)
        # frame the window into 25 ms hops (10 ms stride)
        # compute per-frame RMS, spectral flatness via torchaudio.functional.spectral_centroid + STFT
        # silence_ratio = mean(frame_rms_db < -50)
        # voiced_ratio  = mean(spectral_flatness < 0.4)
        # noise_floor   = np.percentile(frame_rms_db, 10)
        # snr_estimate  = max_frame_rms_db - noise_floor
        ...

    def extract_window(self, src_path, start, end, dst_path):
        # torchaudio.load with frame_offset/num_frames
        # downmix to mono, resample to self._target_sr
        # torchaudio.save(dst_path, ..., format="wav", encoding="PCM_S", bits_per_sample=16)
        ...
```

**Helpers.** `_linear_to_db(x: float) -> float` returning `-inf` for `x <= 0`, else `20*log10(x)`. Keep it as a module-level pure function so the auditor (WP5) can import it for the deterministic clipping check too.

**Edge cases the adapter must handle**

- `start < 0` → clamp to 0.
- `end > duration` → clamp to duration; raise `ValueError` if the resulting window is < 0.05 s.
- File not found → `FileNotFoundError` (let it propagate; the use case treats this as "skip probe").
- Mono input → don't crash on `wav.mean(dim=0)`.

**Tests** (`tests/infrastructure/test_torchaudio_probe_adapter.py`)

Use a synthesized 5-second WAV (white noise mixed with a tone) generated in a fixture:
- `audio_info` returns sane values.
- `window_stats` on a known-silent window returns `silence_ratio > 0.9`.
- `window_stats` on the noisy window returns `silence_ratio < 0.1`.
- `extract_window` writes a file whose duration matches `end-start` within ±5 ms.

Mark the file with `@pytest.mark.skipif(_torchaudio_unavailable, reason=...)` so CI without torchaudio still passes.

**Acceptance.** All four tests green; adapter is the default `AcousticProbePort` in composition (WP7).

---

## 5. WP4 — Pure services: `TranscriptAuditor` + `TranscriptPatcher`

**Files**

- `src/application/services/__init__.py` (new)
- `src/application/services/transcript_auditor.py` (new)
- `src/application/services/transcript_patcher.py` (new)

### 5.1 `TranscriptAuditor`

Pure function over `Transcript`. No I/O.

```python
class TranscriptAuditor:
    def __init__(
        self,
        gap_threshold_s: float = 4.0,
        micro_segment_threshold_s: float = 0.5,
        label_min_occurrences: int = 2,
        label_fuzzy_max_distance: int = 2,
    ): ...

    def audit(self, transcript: Transcript) -> AuditReport: ...

    # Optional cross-fixture audit for SpeakerLabelDrift across multiple transcripts:
    def audit_speaker_corpus(
        self, transcripts: list[Transcript]
    ) -> list[Anomaly]: ...
```

**Rule details (lock these down)**

| Rule | Inputs | Logic |
|---|---|---|
| `DUPLICATE_IDS` | `seg.index` | Group by index; any group with len ≥ 2 → one anomaly listing all those indices. Severity: HIGH. |
| `MID_WORD_BOUNDARY` | adjacent pair (i, i+1) | Trigger when **all** of: (a) same speaker label OR fuzzy-equal, (b) `seg[i].text.rstrip()` does NOT end in `[.!?…]` (note: `?`/`!`/`¿`/`¡`/`.` only — commas don't count), (c) `seg[i+1].text.lstrip()` first non-space char is lowercase OR is `¿`/`¡` AND first word after that punctuation is lowercase. Severity: HIGH. |
| `TIME_GAP` | adjacent pair (i, i+1) | `seg[i+1].start - seg[i].end >= gap_threshold_s`. Severity: MEDIUM. Hint includes gap duration. |
| `MICRO_SEGMENT` | single segment | `seg.duration < micro_segment_threshold_s` AND `not seg.text.rstrip().endswith(any_terminal_punct)`. Severity: LOW. |
| `SPEAKER_LABEL_DRIFT` | label histogram | For labels with count < `label_min_occurrences`, find a label with count ≥ `label_min_occurrences` whose Levenshtein distance ≤ `label_fuzzy_max_distance`. Emit ONE anomaly per cluster, `detail={"canonical": "Joaquin Barraza", "drift": ["Joaquin Barraa"]}`. Severity: MEDIUM. |
| `NON_MONOTONIC_TIMES` | adjacent pair (i, i+1) | `seg[i+1].start < seg[i].start` (NOT `seg[i].end` — overlapping ends are fine). Severity: HIGH. |

**Levenshtein.** Inline a 30-line implementation; do not pull in `python-Levenshtein` for one rule.

**Tests** (`tests/application/test_transcript_auditor.py`) — see §7 fixtures.

### 5.2 `TranscriptPatcher`

Pure function: `Transcript + list[Patch] → Transcript`. Validates each patch, applies in order, **reindexes** all segments at the end so `seg.index` = position in list.

```python
class TranscriptPatcher:
    def apply(
        self, transcript: Transcript, patches: Sequence[Patch]
    ) -> tuple[Transcript, list[Patch]]:
        """Return (patched_transcript, applied_patches). Skips invalid patches and
        annotates the returned patch's `note` with the reason."""
        ...
```

**Validation rules per op**

- `REPLACE_TEXT`: exactly one segment_index; `new_text` required.
- `MERGE`: ≥2 segment_indices, must be contiguous; result = single segment with concatenated text (joined by single space, no double spaces), `start = min(starts)`, `end = max(ends)`, speaker = first segment's speaker (unless `new_speaker` given).
- `SPLIT`: exactly one segment_index; `new_start` is the split point (must lie strictly between segment's start and end); produces two segments — first uses original text up to a heuristic word boundary nearest the time-fraction point (good-enough split; agent can refine with REPLACE_TEXT), second is empty if `new_text` not given.
- `RELABEL`: ≥1 segment_index; `new_speaker` required.
- `RETIME`: exactly one segment_index; `new_start` and/or `new_end` required; `new_start < new_end` after.
- `DELETE`: ≥1 segment_index.
- `INSERT`: `insert_after_index` required (–1 means "at start"); `new_text`, `new_speaker`, `new_start`, `new_end` all required.

**Tests** — round-trip patches against the STG_20 fixture. After `MERGE([8,9,10])` (the shattered question), the patched transcript has 12 segments and ID range [0..11].

**Acceptance.** Auditor + patcher are pure (no I/O imports); tests cover all rules and ops; coverage > 90%.

---

## 6. WP5 — `ValidateAndRefineTranscriptUseCase`

**File**

- `src/application/use_cases/validate_and_refine_transcript.py` (new)

**Dependencies (constructor)**

```python
class ValidateAndRefineTranscriptUseCase:
    def __init__(
        self,
        store: TranscriptStorePort,
        ref_store: ReferenceStorePort,
        narrative_store: NarrativeStorePort,
        reconciler: TranscriptReconcilerPort | None,
        auditor: TranscriptAuditor,
        patcher: TranscriptPatcher,
        processor: AudioProcessorPort,
        diarizer: DiarizationPort,
        asr: ASRPort,
        audio_files: AudioFilePort,
        probe: AcousticProbePort | None,           # None = no acoustic tier
    ): ...
```

**Method**

```python
async def execute(
    self,
    transcript_id: str,
    *,
    canonical_name: str | None = None,
    use_acoustic_probes: bool = True,
    apply_patches: bool = True,
    save_as_new_id: bool = True,                   # False = overwrite
    max_acoustic_windows: int = 8,
    gap_threshold_s: float = 4.0,
    snr_escalation_threshold_db: float = 6.0,
    silence_drop_ratio: float = 0.6,
) -> ValidateAndRefineResult: ...
```

**Pipeline (deterministic order; each step records into the result)**

1. **Load** transcript via `store.load`. If None → raise `ValueError`.
2. **Resolve audio path** via `transcript.metadata["source_audio_path"]` if present, else `transcript.source_file`. If file missing on disk, set `audio_available=False`; the run continues but skips steps 3.audio and 5 entirely.
3. **Audit before** → `auditor.audit(transcript)` → `audit_before`.
4. **Deterministic patches** (no LLM, no audio): build patches for every `DUPLICATE_IDS`, `MICRO_SEGMENT`, `SPEAKER_LABEL_DRIFT`, `NON_MONOTONIC_TIMES`. Apply via patcher.
5. **Reconciler patches** (if `reconciler` and `canonical_name` and references exist): for each remaining `MID_WORD_BOUNDARY` and `TIME_GAP` (filtered to `gap >= gap_threshold_s`), build a window `[start - 1.0, end + 1.0]` clamped to file duration. Group overlapping windows into super-windows. For each super-window, slice the transcript's segments that fall inside, send only those to `reconciler.reconcile` together with the matching reference-slice and narrative-slice. Replace the in-window segments with the reconciler's reconciled segments via patcher (`DELETE` + `INSERT`s in one pass per window). Cap to `max_acoustic_windows / 2` reconciler windows to bound cost.
6. **Acoustic escalation** (if `use_acoustic_probes` and `probe` and `audio_available`): re-audit the in-progress transcript; for each remaining anomaly whose kind is `MID_WORD_BOUNDARY` or `TIME_GAP`, call `probe.window_stats`. Apply this decision tree:
   - `silence_ratio > silence_drop_ratio` → patch: `MERGE` adjacent same-speaker neighbours (drops the gap, keeps continuity).
   - `snr_estimate < snr_escalation_threshold_db` → `probe.extract_window` to a temp clip, `processor.process(clip, params={noise_reduce: True, voice_enhance: True, apply_gain: True})`, `diarizer.diarize(processed_clip, min_speakers=2, max_speakers=2)`, then per resulting turn `asr.transcribe` (with narrative-derived initial_prompt of ≤ 200 chars). Build patches splicing the new turns in; patch via patcher.
   - Otherwise → no acoustic action; record anomaly as "left alone — within tolerance".
7. **Audit after** → `auditor.audit(patched_transcript)` → `audit_after`.
8. **Persist** (if `apply_patches`):
   - If `save_as_new_id=True`, set `patched.transcript_id = f"{transcript_id}_refined_{ts}"`, set `patched.original_transcript_id = transcript_id`, `metadata["refined_from"] = transcript_id`.
   - Always: `metadata["refinement"] = {audit_before_counts, audit_after_counts, patches_applied: int, acoustic_probes_run: int, reconciler_calls: int}`.
   - `store.save(patched)`.

**Result DTO** (Pydantic in `src/application/dto/schemas.py` to match house style)

```python
class ValidateAndRefineResult(BaseModel):
    transcript_id_in: str
    transcript_id_out: str
    audit_before: AuditReportDTO
    audit_after: AuditReportDTO
    patches_applied: list[PatchDTO]
    acoustic_probes_run: int
    reconciler_calls: int
    audio_available: bool
    notes: list[str]
```

**Tests** (`tests/application/test_validate_and_refine_transcript.py`)

Use the STG_20 fixture + a fake reconciler that returns canned reconciled segments + the `FakeAcousticProbe` from WP2.

| Test | Assertion |
|---|---|
| `test_deterministic_only` | use_acoustic_probes=False, reconciler=None → audit_after has 0 DUPLICATE_IDS, 0 SPEAKER_LABEL_DRIFT, 0 NON_MONOTONIC_TIMES. MID_WORD_BOUNDARY and TIME_GAP unchanged. |
| `test_with_reconciler` | reconciler returns 2 reconciled segments for the 38–43s window → MID_WORD_BOUNDARY count drops to 0. |
| `test_acoustic_silence_drop` | probe returns `silence_ratio=0.85` for the 13.5–17.5 gap → MERGE patch applied; TIME_GAP count drops by 1. |
| `test_acoustic_low_snr_escalation` | probe returns `snr_estimate=3.0` → fake `processor.process` + fake `diarizer.diarize` are called once; assert call args. |
| `test_audio_missing` | source file missing → audio_available=False, no probe / no asr / no diarizer calls; deterministic patches still applied. |
| `test_save_as_new_id` | new transcript_id contains "_refined_"; original_transcript_id == input id; original transcript still loadable. |
| `test_max_acoustic_windows` | 12 anomalies, max=3 → at most 3 probe calls. |

**Acceptance.** All 7 tests green. No real torchaudio, no real Whisper, no real Pyannote in this WP's tests (use fakes).

---

## 7. WP6 — MCP tools

**File**

- `src/mcp/servers/transcripts_server.py` (extend)

Three new tools. Reuse `_RUNTIME` and `_STORE` already at module top; pull the new use case from runtime (added in WP7).

```python
_VALIDATE_REFINE_USE_CASE = _RUNTIME.validate_refine_use_case
_AUDITOR = _RUNTIME.auditor
_PATCHER = _RUNTIME.patcher

@mcp.tool()
def audit_transcript(transcript_id: str) -> dict[str, Any]:
    """Run structural audit on a stored transcript. No audio, no LLM.
    Returns AuditReport-shaped dict."""

@mcp.tool()
async def validate_and_refine_transcript(
    transcript_id: str,
    canonical_name: str | None = None,
    use_acoustic_probes: bool = True,
    apply_patches: bool = True,
    save_as_new_id: bool = True,
    max_acoustic_windows: int = 8,
) -> dict[str, Any]:
    """Audit + auto-fix deterministic anomalies + reconcile flagged windows
    + (optionally) probe audio and re-diarize/re-ASR low-SNR clips.
    Returns ValidateAndRefineResult-shaped dict."""

@mcp.tool()
def patch_transcript_segments(
    transcript_id: str,
    patches: list[dict[str, Any]],
    save_as_new_id: bool = True,
) -> dict[str, Any]:
    """Agent-supplied patches. Each patch dict must include 'op' and 'segment_indices';
    other fields per Patch dataclass. Returns the new transcript dict and
    the list of applied patches."""
```

**Tool tests** (`tests/mcp/test_validate_refine_mcp.py`)

Smoke-test each tool by calling them directly (the FastMCP server exposes the underlying functions). Use the STG_20 fixture as the stored transcript. Assert:
- `audit_transcript` returns `counts_by_kind` matching §8.1.
- `patch_transcript_segments` with one MERGE patch produces a transcript with N-1 segments.

**Acceptance.** Three tools registered; smoke tests green.

---

## 8. WP7 — Wiring, settings, requirements

**Files**

- `src/config.py` (extend)
- `src/composition.py` (extend)
- `requirements.txt` (extend)
- `Makefile` (one new target)

**Settings additions** (`src/config.py`)

```python
ENABLE_ACOUSTIC_PROBES: bool = os.getenv("ENABLE_ACOUSTIC_PROBES", "true").lower() == "true"
ACOUSTIC_PROBE_TARGET_SR: int = int(os.getenv("ACOUSTIC_PROBE_TARGET_SR", "16000"))
REFINE_GAP_THRESHOLD_S: float = float(os.getenv("REFINE_GAP_THRESHOLD_S", "4.0"))
REFINE_SNR_ESCALATION_DB: float = float(os.getenv("REFINE_SNR_ESCALATION_DB", "6.0"))
REFINE_SILENCE_DROP_RATIO: float = float(os.getenv("REFINE_SILENCE_DROP_RATIO", "0.6"))
REFINE_MAX_ACOUSTIC_WINDOWS: int = int(os.getenv("REFINE_MAX_ACOUSTIC_WINDOWS", "8"))
```

**Composition additions** (`src/composition.py`)

In `transcriptionRuntime` dataclass:

```python
auditor: Any = None
patcher: Any = None
probe_adapter: Any = None
validate_refine_use_case: Any = None
```

In `build_runtime()` after the existing reconciler block:

```python
from .application.services.transcript_auditor import TranscriptAuditor
from .application.services.transcript_patcher import TranscriptPatcher
from .application.use_cases.validate_and_refine_transcript import (
    ValidateAndRefineTranscriptUseCase,
)

runtime.auditor = TranscriptAuditor()
runtime.patcher = TranscriptPatcher()

if settings.ENABLE_ACOUSTIC_PROBES:
    try:
        from .infrastructure.torchaudio_probe_adapter import TorchaudioProbeAdapter
        runtime.probe_adapter = TorchaudioProbeAdapter(
            target_sample_rate=settings.ACOUSTIC_PROBE_TARGET_SR,
        )
        logger.info("[refine] acoustic probes enabled (torchaudio)")
    except Exception as exc:
        logger.warning("[refine] acoustic probes disabled — torchaudio import failed: %s", exc)
        runtime.probe_adapter = None

runtime.validate_refine_use_case = ValidateAndRefineTranscriptUseCase(
    store=store_adapter,
    ref_store=ref_store_adapter,
    narrative_store=narrative_store_adapter,
    reconciler=runtime.reconciler_adapter,    # may be None
    auditor=runtime.auditor,
    patcher=runtime.patcher,
    processor=processor_adapter,
    diarizer=diarizer_adapter,
    asr=asr_adapter,
    audio_files=audio_file_adapter,
    probe=runtime.probe_adapter,              # may be None
)
```

**Makefile**

```makefile
test-refine:
	pytest tests/application/test_transcript_auditor.py \
	       tests/application/test_transcript_patcher.py \
	       tests/application/test_validate_and_refine_transcript.py \
	       tests/mcp/test_validate_refine_mcp.py -v
```

**Acceptance.** `make test-refine` green. `python -m src.mcp.servers.transcripts_server` boots without errors when `ENABLE_ACOUSTIC_PROBES=false`.

---

## 9. Test fixtures (frozen — agents must not modify)

### 9.1 `tests/fixtures/aeropuerto_STG_20.json`

Verbatim copy of the file the user already shared. The auditor must produce:

| Anomaly | Expected hits |
|---|---|
| `DUPLICATE_IDS` | 2 (id "7" twice; id "9" twice — note these are JSON `id` collisions; map to the `index` field after import) |
| `MID_WORD_BOUNDARY` | 1 (segments around 38–43s: id 8 → id 9 → id 7; same speaker, no terminal punct, lowercase continuation) |
| `TIME_GAP` | 2 (13.53→17.5 inside segment_1 fixture; 42.86→52.97 in full transcript) — only the second qualifies in the full file |
| `MICRO_SEGMENT` | 1 (id 9 `" ¿Nadie te "` — duration 0.6s but ends without terminal punct → this is borderline; tighten threshold to 0.7s if needed during dev) |
| `SPEAKER_LABEL_DRIFT` | 0 within the single transcript; 1 when audited cross-fixture with `aeropuerto_STG_20_segment_1.json` (`Joaquin Barraa` ↔ `Joaquin Barraza`) |
| `NON_MONOTONIC_TIMES` | 0 |

### 9.2 `tests/fixtures/aeropuerto_STG_20_segment_1.json`

Verbatim copy of the segment file. Used for cross-fixture speaker-drift test.

### 9.3 `tests/fixtures/incident_narrative_STG_20.txt`

Verbatim copy of the narrative file. Used as `IncidentNarrative.text` in the reconciler-path test.

### 9.4 Synthetic audio fixture

`tests/fixtures/_make_audio.py` — pytest fixture that, on demand, synthesizes a 60-second WAV with: 0–13s tone, 13–18s silence, 18–43s tone+noise (low SNR), 43–53s silence, 53–60s tone. Used by WP3 adapter tests and (optionally) the integration smoke test.

---

## 10. Sequencing & ownership

Recommended agent assignment — each WP is a separate task:

1. **WP1** (entities) — small, ~30 min. Blocks everything.
2. **WP2** (port + fake) — small, ~30 min. Depends on WP1.
3. **WP3** (torchaudio adapter) — medium, ~2 h. Depends on WP2. Can run in parallel with WP4/WP5.
4. **WP4** (auditor + patcher pure services) — medium, ~3 h. Depends on WP1. Can run in parallel with WP3.
5. **WP5** (use case) — large, ~3 h. Depends on WP1, WP2, WP4. Fakes for WP3.
6. **WP6** (MCP tools) — small, ~1 h. Depends on WP5.
7. **WP7** (wiring + settings + Makefile) — small, ~1 h. Depends on all above.

Total ≈ 1.5 days of focused work if done serially; <1 day if WP3 and WP4 run in parallel.

---

## 11. Risks & guardrails

- **torchaudio install on macOS-arm64**: known to be flaky. WP7 wraps the import in try/except so the service still boots. Document in `RUNPOD_SETUP.md` follow-up.
- **Reconciler cost runaway**: capped by `max_acoustic_windows / 2`. The result DTO surfaces `reconciler_calls` so the agent sees the cost.
- **Patch application bugs corrupting transcripts**: every refinement run defaults to `save_as_new_id=True` so the original is never overwritten. The agent must opt in to in-place.
- **Whisper model warm-up inside a probe**: WP5 step 6 calls `asr.transcribe` on small clips. Whisper is already warm in the existing runtime — fine. If `transcribe_audio` hasn't been called yet, the first probe pays the model-load cost; acceptable.
- **Audio file path drift**: `transcript.source_file` may point at the *processed* WAV from the original run, not the original. The use case must prefer `metadata["source_audio_path"]` if present, else `source_file`. WP5 already does this; the agent implementing WP5 should grep `whisper_adapter.py`/`transcribe_audio.py` to confirm what gets stored in `source_file` and either fix it there (small bonus) or document the precedence.

---

## 12. Out of scope (parking lot)

- HTTP/FastAPI endpoint mirroring the new MCP tools.
- Calling the audio project's MCP server as an external service (we use torchaudio in-process). Revisit if torchaudio in-process turns out to bloat the deployable image too much.
- Hooking into the `torchaudio_mcp` greedy ASR (`transcription_transcribe_greedy`) as an alternative ASR for low-confidence windows. Could be a second `ASRPort` later.
- UI for reviewing audit reports.
- Auto-rerunning Qdrant indexing after refinement.

---

That's the spec. Three things to confirm before handing off:

1. Default for `ENABLE_ACOUSTIC_PROBES` — I have it as `true`. If you'd rather ship dark and flip it on after eval, say so.
2. `save_as_new_id` default — I have it as `true`. Safest, but it doubles disk usage. Want overwrite as the default?
3. Are you OK with adding `torch + torchaudio` as runtime deps to this service, or should they move to an `optional-dependencies` extra?