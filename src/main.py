"""SA-Pinocchio — Composition Root.

Wires domain ports → infrastructure adapters → use cases → routers.
This file is the ONLY place where all layers know about each other.
"""
import asyncio
import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .composition import build_runtime
from .config import settings
from .logging_setup import setup_logging
from .presentation.routers.diarization import init_diarization_router
from .presentation.routers.diarization import router as diarization_router

# Presentation routers
from .presentation.routers.health import router as health_router
from .presentation.routers.parameters import router as parameters_router
from .presentation.routers.transcription import init_transcription_router
from .presentation.routers.transcription import router as transcription_router
from .presentation.routers.transcripts import init_transcript_router
from .presentation.routers.transcripts import router as transcripts_router

# ── Setup ────────────────────────────────────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)

runtime = build_runtime()

# ── Router Injection ─────────────────────────────────────────────────────
init_diarization_router(runtime.excerpt_use_case, runtime.audio_file_adapter, settings.TRANSCRIPT_DIR)
init_transcription_router(runtime.transcribe_use_case, settings.ORIGINALS_DIR)
init_transcript_router(
    runtime.analyze_use_case,
    runtime.search_use_case,
    runtime.store_adapter,
    runtime.qdrant_adapter,
)

# ── FastAPI App ──────────────────────────────────────────────────────────
app = FastAPI(title="SA Pinocchio Transcription API")

# CORS — explicit origins, not wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(parameters_router)
app.include_router(diarization_router)
app.include_router(transcription_router)
app.include_router(transcripts_router)

# Serve static data directories
app.mount("/audio", StaticFiles(directory=settings.AUDIO_DIR), name="audio")
app.mount("/originals", StaticFiles(directory=settings.ORIGINALS_DIR), name="originals")
app.mount("/transcripts", StaticFiles(directory=settings.TRANSCRIPT_DIR), name="transcripts")


@app.on_event("startup")
async def preload():
    """Kick off non-blocking background preload of heavy models."""
    log = logging.getLogger("startup")
    t = time.time()

    async def _preload():
        try:
            await asyncio.to_thread(
                runtime.model_manager.get_diarization_pipeline,
                settings.RESOLVED_HF_TOKEN,
            )
            await asyncio.to_thread(runtime.model_manager.get_whisper_model, "small")
            log.info(f"Preload done in {time.time()-t:.2f}s")
        except Exception as e:
            log.warning(f"Preload skipped: {e}")

    asyncio.create_task(_preload())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
