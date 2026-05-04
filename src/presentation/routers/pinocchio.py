"""Pinocchio frontend router.

Serves the Pinocchio HTML UI at `/` and `/pinocchio`, and exposes
`/api/pinocchio/*` aliases that 307-redirect to the canonical backend
routes (`/api/diarization/*`, `/api/transcripts/*`). 307 preserves both
HTTP method and request body, so multipart uploads work transparently.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pinocchio"])

# Resolve template path once
_TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "pinocchio.html"


@router.get("/", include_in_schema=False)
@router.get("/pinocchio", include_in_schema=False)
async def serve_pinocchio_ui() -> FileResponse:
    if not _TEMPLATE_PATH.exists():
        raise HTTPException(status_code=404, detail=f"UI template missing: {_TEMPLATE_PATH}")
    return FileResponse(str(_TEMPLATE_PATH), media_type="text/html")


# ── /api/pinocchio/* aliases (307 preserves method + body) ────────────────


def _redirect(target: str) -> RedirectResponse:
    return RedirectResponse(url=target, status_code=307)


@router.post("/api/pinocchio/transcribe", include_in_schema=False)
async def alias_transcribe() -> RedirectResponse:
    return _redirect("/api/diarization/transcribe")


@router.post("/api/pinocchio/transcribe/async", include_in_schema=False)
async def alias_transcribe_async() -> RedirectResponse:
    return _redirect("/api/diarization/transcribe/async")


@router.post("/api/pinocchio/transcribe/guided", include_in_schema=False)
async def alias_transcribe_guided() -> RedirectResponse:
    return _redirect("/api/diarization/transcribe/guided")


@router.post("/api/pinocchio/transcribe/guided/async", include_in_schema=False)
async def alias_transcribe_guided_async() -> RedirectResponse:
    return _redirect("/api/diarization/transcribe/guided/async")


@router.get("/api/pinocchio/transcripts", include_in_schema=False)
async def alias_list_transcripts() -> RedirectResponse:
    return _redirect("/api/transcripts")


@router.get("/api/pinocchio/transcripts/{transcript_id}", include_in_schema=False)
async def alias_get_transcript(transcript_id: str) -> RedirectResponse:
    return _redirect(f"/api/transcripts/{transcript_id}")


# ── Endpoints the legacy UI expects but that aren't implemented here ──────
# Return a structured 501 so the frontend shows a clear error rather than
# falling back to noisy network failures.


_NOT_IMPLEMENTED = {
    "error": "not_implemented",
    "detail": (
        "This endpoint is part of the legacy Pinocchio gateway and is not "
        "available in this transcription service build. Use the diarization "
        "and guided transcription endpoints instead."
    ),
}


@router.post("/api/pinocchio/transcribe/pyannote", include_in_schema=False)
async def stub_pyannote() -> JSONResponse:
    return JSONResponse(_NOT_IMPLEMENTED, status_code=501)


@router.post("/api/pinocchio/voiceprint_from_file", include_in_schema=False)
async def stub_voiceprint() -> JSONResponse:
    return JSONResponse(_NOT_IMPLEMENTED, status_code=501)
