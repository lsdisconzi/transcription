"""Transcript intelligence router — analyze, search, list, SSE stream."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.application.dto.schemas import AnalyzeRequest, SearchRequest
from src.domain.entities.transcript import Segment, Speaker, Transcript

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])

# Injected by composition root
_analyze_use_case = None
_search_use_case = None
_store = None
_index = None
_auditor = None
_patcher = None
_validate_refine_use_case = None


def init_transcript_router(
    analyze_use_case,
    search_use_case,
    store,
    index=None,
    *,
    auditor=None,
    patcher=None,
    validate_refine_use_case=None,
):
    global _analyze_use_case, _search_use_case, _store, _index
    global _auditor, _patcher, _validate_refine_use_case
    _analyze_use_case = analyze_use_case
    _search_use_case = search_use_case
    _store = store
    _index = index
    _auditor = auditor
    _patcher = patcher
    _validate_refine_use_case = validate_refine_use_case


class ImportSegmentPayload(BaseModel):
    index: int | None = None
    speaker: str | None = None
    start: float | int | None = 0.0
    end: float | int | None = None
    text: str | None = ""


class ImportRunPayload(BaseModel):
    transcript_id: str | None = None
    source_file: str | None = None
    filename: str | None = None
    language: str | None = None
    timestamp: str | None = None
    provider: str | None = None
    metadata: dict | None = None
    segments: list[ImportSegmentPayload] = Field(default_factory=list)


class ImportTranscriptsPayload(BaseModel):
    runs: list[ImportRunPayload] = Field(default_factory=list)
    overwrite: bool = False
    # When True, derive transcript_id from the source filename (stem), falling
    # back to the caller-supplied transcript_id only if no filename is given.
    rename_by_filename: bool = True


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename_stem(name: str) -> str:
    """Turn a user-facing filename into a safe transcript_id stem.

    Strips directory components, drops the extension, and replaces unsafe
    characters with `_`. Returns empty string when nothing usable remains.
    """
    if not name:
        return ""
    base = os.path.basename(str(name)).strip()
    stem, _ext = os.path.splitext(base)
    cleaned = _SAFE_NAME_RE.sub("_", stem).strip("._-")
    return cleaned[:180]


# ── List transcripts ─────────────────────────────────────────────────────


@router.get("")
async def list_transcripts():
    """Return all transcript IDs."""
    ids = _store.list_ids()
    return {"transcripts": sorted(ids, reverse=True)}


# ── Get single transcript ────────────────────────────────────────────────


@router.get("/{transcript_id}")
async def get_transcript(transcript_id: str):
    """Load and return a transcript by ID."""
    transcript = _store.load(transcript_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail=f"Transcript not found: {transcript_id}")
    return {
        "transcript_id": transcript.transcript_id,
        "source_file": transcript.source_file,
        "language": transcript.language,
        "timestamp": transcript.timestamp,
        "provider": transcript.provider,
        "original_transcript_id": transcript.original_transcript_id,
        "metadata": transcript.metadata or {},
        "segments": [
            {
                "index": s.index,
                "speaker": s.speaker.label,
                "start": s.start,
                "end": s.end,
                "duration": s.duration,
                "text": s.text,
            }
            for s in transcript.segments
        ],
    }


@router.post("/import")
async def import_transcripts(payload: ImportTranscriptsPayload):
    """Import one or more transcripts into persistent JSON store."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Transcript store not initialized")
    if not payload.runs:
        raise HTTPException(status_code=400, detail="No runs provided for import")

    existing_ids = set(_store.list_ids())
    imported_ids: list[str] = []
    skipped: list[dict] = []
    errors: list[dict] = []

    for idx, run in enumerate(payload.runs):
        try:
            segments: list[Segment] = []
            for seg_idx, seg in enumerate(run.segments):
                start = float(seg.start or 0.0)
                if start < 0:
                    start = 0.0

                end_raw = seg.end if seg.end is not None else start
                end = float(end_raw)
                if end < start:
                    end = start

                speaker_label = (seg.speaker or f"SPEAKER_{seg_idx:02d}").strip() or f"SPEAKER_{seg_idx:02d}"
                segment_index = seg.index if seg.index is not None else seg_idx
                segments.append(
                    Segment(
                        index=int(segment_index),
                        speaker=Speaker(label=speaker_label),
                        start=start,
                        end=end,
                        text=str(seg.text or ""),
                    )
                )

            if not segments:
                skipped.append({"index": idx, "reason": "empty_segments"})
                continue

            incoming_id = (run.transcript_id or "").strip()
            source_file = (run.source_file or run.filename or "").strip()
            filename_stem = _sanitize_filename_stem(run.filename or run.source_file or "")

            # Prefer filename-based id (WhatsApp audio names already encode
            # date/time), fall back to caller-supplied id, finally generate.
            if payload.rename_by_filename and filename_stem:
                desired_id = filename_stem
            elif incoming_id:
                desired_id = incoming_id
            elif filename_stem:
                desired_id = filename_stem
            else:
                desired_id = f"imported_{int(time.time() * 1000)}_{idx + 1}"

            transcript_id = desired_id
            if not payload.overwrite and transcript_id in existing_ids:
                nonce = 1
                while transcript_id in existing_ids:
                    nonce += 1
                    transcript_id = f"{desired_id}_{nonce}"

            if not payload.overwrite and transcript_id in existing_ids:
                skipped.append(
                    {
                        "index": idx,
                        "transcript_id": transcript_id,
                        "reason": "already_exists",
                    }
                )
                continue

            transcript = Transcript(
                transcript_id=transcript_id,
                segments=segments,
                source_file=source_file,
                language=(run.language or "es"),
                metadata=(run.metadata or {}),
                timestamp=(run.timestamp or ""),
                provider=(run.provider or ""),
                original_transcript_id=(incoming_id if incoming_id and incoming_id != transcript_id else ""),
            )
            _store.save(transcript)
            existing_ids.add(transcript_id)
            imported_ids.append(transcript_id)
        except Exception as e:
            errors.append(
                {
                    "index": idx,
                    "transcript_id": run.transcript_id,
                    "error": str(e),
                }
            )

    return {
        "total_runs": len(payload.runs),
        "imported": len(imported_ids),
        "imported_ids": imported_ids,
        "skipped": skipped,
        "errors": errors,
    }


# ── Analyze with Claude ──────────────────────────────────────────────────


@router.post("/analyze")
async def analyze_transcript(payload: AnalyzeRequest):
    """Run Claude analysis on a transcript."""
    if _analyze_use_case is None:
        raise HTTPException(
            status_code=503,
            detail="Transcript analysis not configured. Set DEEPSEEK_API_KEY or ANTHROPIC_API_KEY.",
        )
    try:
        result = await _analyze_use_case.execute(
            payload.transcript_id, instructions=payload.instructions
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("[error] analysis failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Semantic search ──────────────────────────────────────────────────────


@router.post("/search")
async def search_transcripts(payload: SearchRequest):
    """Semantic search across all indexed transcripts."""
    if _search_use_case is None:
        raise HTTPException(
            status_code=503,
            detail="Transcript search not configured. Set QDRANT_URL.",
        )
    try:
        result = await _search_use_case.execute(payload.query, limit=payload.limit)
        return result.model_dump()
    except Exception as e:
        logger.exception("[error] search failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Re-index a transcript ───────────────────────────────────────────────


@router.post("/{transcript_id}/index")
async def index_transcript(transcript_id: str):
    """Manually index (or re-index) a transcript into Qdrant."""
    if _index is None:
        raise HTTPException(
            status_code=503,
            detail="Vector indexing not configured. Set QDRANT_URL.",
        )
    transcript = _store.load(transcript_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail=f"Transcript not found: {transcript_id}")

    n = await _index.index(transcript)
    return {"transcript_id": transcript_id, "segments_indexed": n}


# ── Bulk re-index all transcripts ────────────────────────────────────────


@router.post("/index-all")
async def index_all_transcripts():
    """Re-index all stored transcripts into Qdrant (admin operation)."""
    if _index is None:
        raise HTTPException(
            status_code=503,
            detail="Vector indexing not configured. Set QDRANT_URL.",
        )
    ids = _store.list_ids()
    total = 0
    errors = []
    for tid in ids:
        transcript = _store.load(tid)
        if transcript is None:
            continue
        try:
            n = await _index.index(transcript)
            total += n
        except Exception as e:
            errors.append({"transcript_id": tid, "error": str(e)})

    return {
        "transcripts_processed": len(ids),
        "segments_indexed": total,
        "errors": errors,
    }


# ── SSE: Stream transcription progress ──────────────────────────────────

# In-memory progress store (keyed by transcript-in-progress job id)
_progress: dict[str, list[dict]] = {}
_jobs: dict[str, dict] = {}
_JOB_RETENTION_SEC = 3600


def _now_ts() -> float:
    return time.time()


def _cleanup_jobs() -> None:
    now = _now_ts()
    stale_ids = []
    for job_id, job in _jobs.items():
        updated_at = float(job.get("updated_at", now))
        if now - updated_at > _JOB_RETENTION_SEC:
            stale_ids.append(job_id)
    for job_id in stale_ids:
        _jobs.pop(job_id, None)
        _progress.pop(job_id, None)


def start_progress_job(job_id: str, filename: str | None = None) -> None:
    """Initialize an in-memory progress job with queued status."""
    _cleanup_jobs()
    now = _now_ts()
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "stage": "upload",
        "progress": 0,
        "message": "Job enfileirado",
        "filename": filename,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "ended_at": None,
        "elapsed_s": 0.0,
        "result": None,
        "error": None,
    }
    _progress[job_id] = []
    emit_progress(job_id, "queued", {
        "job_id": job_id,
        "status": "queued",
        "stage": "upload",
        "progress": 0,
        "message": "Job enfileirado",
    })


def update_progress_job(
    job_id: str,
    *,
    stage: str,
    progress: int,
    message: str,
    status: str = "running",
    extra: dict | None = None,
) -> None:
    """Update in-memory job status and emit SSE progress event."""
    now = _now_ts()
    job = _jobs.get(job_id)
    if job is None:
        start_progress_job(job_id)
        job = _jobs[job_id]

    if job.get("started_at") is None and status == "running":
        job["started_at"] = now

    job.update({
        "status": status,
        "stage": stage,
        "progress": max(0, min(100, int(progress))),
        "message": message,
        "updated_at": now,
    })

    started_at = job.get("started_at") or job.get("created_at") or now
    job["elapsed_s"] = round(max(0.0, now - float(started_at)), 2)

    payload = {
        "job_id": job_id,
        "status": job["status"],
        "stage": job["stage"],
        "progress": job["progress"],
        "message": job["message"],
        "elapsed_s": job["elapsed_s"],
    }
    if extra:
        payload.update(extra)

    emit_progress(job_id, "progress", payload)


def complete_progress_job(job_id: str, result: dict) -> None:
    """Mark job complete, attach final result, and emit terminal SSE event."""
    now = _now_ts()
    job = _jobs.get(job_id)
    if job is None:
        start_progress_job(job_id)
        job = _jobs[job_id]

    started_at = job.get("started_at") or job.get("created_at") or now
    elapsed_s = round(max(0.0, now - float(started_at)), 2)

    job.update({
        "status": "done",
        "stage": "transcription",
        "progress": 100,
        "message": "Concluído",
        "result": result,
        "updated_at": now,
        "ended_at": now,
        "elapsed_s": elapsed_s,
        "error": None,
    })

    emit_progress(job_id, "done", {
        "job_id": job_id,
        "status": "done",
        "stage": "transcription",
        "progress": 100,
        "message": "Concluído",
        "elapsed_s": elapsed_s,
    })


def fail_progress_job(job_id: str, error: str) -> None:
    """Mark job failed and emit terminal error SSE event."""
    now = _now_ts()
    job = _jobs.get(job_id)
    if job is None:
        start_progress_job(job_id)
        job = _jobs[job_id]

    started_at = job.get("started_at") or job.get("created_at") or now
    elapsed_s = round(max(0.0, now - float(started_at)), 2)

    job.update({
        "status": "error",
        "message": error,
        "updated_at": now,
        "ended_at": now,
        "elapsed_s": elapsed_s,
        "error": error,
    })

    emit_progress(job_id, "error", {
        "job_id": job_id,
        "status": "error",
        "message": error,
        "stage": job.get("stage") or "transcription",
        "progress": int(job.get("progress") or 0),
        "elapsed_s": elapsed_s,
    })


def get_progress_job(job_id: str) -> dict | None:
    """Return current in-memory status for a job, if any."""
    _cleanup_jobs()
    job = _jobs.get(job_id)
    if job is None:
        return None
    return dict(job)


def emit_progress(job_id: str, event_type: str, data: dict) -> None:
    """Called by the transcription use case to emit progress events."""
    if job_id not in _progress:
        _progress[job_id] = []
    _progress[job_id].append({"event": event_type, "data": data})


@router.get("/status/{job_id}")
async def get_progress_status(job_id: str):
    """Return current transcription job progress/status snapshot."""
    job = get_progress_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@router.get("/stream/{job_id}")
async def stream_progress(job_id: str, request: Request):
    """SSE endpoint — streams transcription progress events."""

    async def event_generator():
        cursor = 0
        while True:
            if await request.is_disconnected():
                break
            events = _progress.get(job_id, [])
            while cursor < len(events):
                ev = events[cursor]
                yield {
                    "event": ev["event"],
                    "data": json.dumps(ev["data"]),
                }
                cursor += 1
                if ev["event"] in ("done", "error"):
                    # Clean up after terminal events
                    _progress.pop(job_id, None)
                    return
            await asyncio.sleep(0.3)

    return EventSourceResponse(event_generator())


# ── Validate / Refine / Patch ────────────────────────────────────────────


class PatchPayload(BaseModel):
    op: str
    segment_indices: list[int] = Field(default_factory=list)
    new_text: str | None = None
    new_speaker: str | None = None
    new_start: float | None = None
    new_end: float | None = None
    insert_after_index: int | None = None
    note: str | None = ""


class RefinePayload(BaseModel):
    canonical_name: str | None = None
    use_acoustic_probes: bool = True
    apply_patches: bool = True
    save_as_new_id: bool = True
    max_acoustic_windows: int = 8


class PatchSegmentsPayload(BaseModel):
    patches: list[PatchPayload] = Field(default_factory=list)
    save_as_new_id: bool = True


def _audit_to_payload(report) -> dict:
    return {
        "transcript_id": report.transcript_id,
        "counts_by_kind": report.kind_counts(),
        "counts_by_severity": report.severity_counts(),
        "anomalies": [
            {
                "kind": a.kind.value,
                "severity": a.severity.value,
                "segment_indices": list(a.segment_indices),
                "start": a.start,
                "end": a.end,
                "hint": a.hint,
                "detail": a.detail_dict(),
            }
            for a in report.anomalies
        ],
    }


@router.post("/{transcript_id}/audit")
async def audit_transcript_route(transcript_id: str):
    """Run structural audit on a stored transcript. No audio, no LLM."""
    if _auditor is None or _store is None:
        raise HTTPException(status_code=503, detail="Auditor not configured.")
    transcript = _store.load(transcript_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail=f"Transcript not found: {transcript_id}")
    return _audit_to_payload(_auditor.audit(transcript))


@router.post("/{transcript_id}/refine")
async def refine_transcript_route(transcript_id: str, payload: RefinePayload | None = None):
    """Audit + auto-fix + (optional) acoustic escalation. Returns ValidateAndRefineResult."""
    if _validate_refine_use_case is None:
        raise HTTPException(status_code=503, detail="Validate/refine use case not configured.")
    body = payload or RefinePayload()
    try:
        result = await _validate_refine_use_case.execute(
            transcript_id,
            canonical_name=body.canonical_name,
            use_acoustic_probes=body.use_acoustic_probes,
            apply_patches=body.apply_patches,
            save_as_new_id=body.save_as_new_id,
            max_acoustic_windows=body.max_acoustic_windows,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("[error] refine failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    return result.model_dump()


@router.post("/{transcript_id}/patch")
async def patch_transcript_route(transcript_id: str, payload: PatchSegmentsPayload):
    """Apply an explicit list of patches and persist."""
    if _patcher is None or _store is None:
        raise HTTPException(status_code=503, detail="Patcher not configured.")
    from dataclasses import replace as _replace

    from src.domain.entities.patch import Patch, PatchOp

    transcript = _store.load(transcript_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail=f"Transcript not found: {transcript_id}")

    parsed: list[Patch] = []
    for raw in payload.patches:
        try:
            op = PatchOp(raw.op)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"unknown patch op: {raw.op}") from exc
        parsed.append(
            Patch(
                op=op,
                segment_indices=tuple(int(i) for i in raw.segment_indices),
                new_text=raw.new_text,
                new_speaker=raw.new_speaker,
                new_start=raw.new_start,
                new_end=raw.new_end,
                insert_after_index=raw.insert_after_index,
                note=raw.note or "",
            )
        )

    patched, applied = _patcher.apply(transcript, parsed)
    if payload.save_as_new_id:
        new_id = f"{transcript_id}_patched_{int(time.time())}"
        patched = _replace(
            patched,
            transcript_id=new_id,
            original_transcript_id=transcript_id,
        )
    _store.save(patched)

    return {
        "transcript_id_in": transcript_id,
        "transcript_id_out": patched.transcript_id,
        "patches_applied": [
            {
                "op": p.op.value,
                "segment_indices": list(p.segment_indices),
                "new_text": p.new_text,
                "new_speaker": p.new_speaker,
                "new_start": p.new_start,
                "new_end": p.new_end,
                "insert_after_index": p.insert_after_index,
                "note": p.note,
            }
            for p in applied
        ],
    }
