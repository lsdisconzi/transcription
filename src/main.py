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

from .application.use_cases.diarize_excerpt import DiarizeExcerptUseCase
from .application.use_cases.guided_transcribe import ReferenceGuidedTranscribeUseCase

# Application use cases
from .application.use_cases.transcribe_audio import TranscribeAudioUseCase
from .config import settings
from .infrastructure.audio_file_adapter import AudioFileAdapter
from .infrastructure.json_store import JSONTranscriptStore

# Infrastructure adapters
from .infrastructure.model_manager import ModelManager
from .infrastructure.narrative_store_adapter import NarrativeStoreAdapter
from .infrastructure.pyannote_adapter import PyAnnoteDiarizerAdapter
from .infrastructure.pydub_processor import PydubProcessorAdapter
from .infrastructure.reference_store_adapter import ReferenceStoreAdapter
from .infrastructure.whisper_adapter import WhisperASRAdapter
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

# ── Infrastructure Wiring ────────────────────────────────────────────────
model_manager = ModelManager()
asr_adapter = WhisperASRAdapter(model_manager)
diarizer_adapter = PyAnnoteDiarizerAdapter(model_manager, settings.RESOLVED_HF_TOKEN)
processor_adapter = PydubProcessorAdapter()
store_adapter = JSONTranscriptStore(settings.TRANSCRIPT_DIR)
audio_file_adapter = AudioFileAdapter()
ref_store_adapter = ReferenceStoreAdapter(settings.REFERENCE_DIR)
narrative_store_adapter = NarrativeStoreAdapter(settings.NARRATIVE_DIR)

# AI-Native adapters (optional — graceful degradation if not configured)
claude_adapter = None
qdrant_adapter = None
reconciler_adapter = None
analyze_use_case = None
search_use_case = None

if settings.ANTHROPIC_API_KEY:
    from .application.use_cases.analyze_transcript import AnalyzeTranscriptUseCase
    from .infrastructure.claude_analyzer import ClaudeAnalyzerAdapter
    from .infrastructure.claude_reconciler import ClaudeReconcilerAdapter

    claude_adapter = ClaudeAnalyzerAdapter(
        api_key=settings.ANTHROPIC_API_KEY,
        model=settings.ANTHROPIC_MODEL,
    )
    analyze_use_case = AnalyzeTranscriptUseCase(
        analyzer=claude_adapter, store=store_adapter
    )
    logger.info("[ai] Claude analyzer configured (model=%s)", settings.ANTHROPIC_MODEL)

    if settings.DEEPSEEK_API_KEY:
        from .infrastructure.deepseek_reconciler import DeepSeekReconcilerAdapter

        reconciler_adapter = DeepSeekReconcilerAdapter(
            api_key=settings.DEEPSEEK_API_KEY,
            model=settings.DEEPSEEK_RECONCILER_MODEL,
        )
        logger.info(
            "[ai] DeepSeek reconciler configured (model=%s)",
            settings.DEEPSEEK_RECONCILER_MODEL,
        )
    else:
        reconciler_adapter = ClaudeReconcilerAdapter(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.ANTHROPIC_MODEL,
        )
        logger.info(
            "[ai] Claude reconciler configured (model=%s)",
            settings.ANTHROPIC_MODEL,
        )
elif settings.DEEPSEEK_API_KEY:
    # Fallback: use DeepSeek for both analysis and reconciliation
    from .application.use_cases.analyze_transcript import AnalyzeTranscriptUseCase
    from .infrastructure.deepseek_analyzer import DeepSeekAnalyzerAdapter
    from .infrastructure.deepseek_reconciler import DeepSeekReconcilerAdapter

    _ds_analyzer = DeepSeekAnalyzerAdapter(
        api_key=settings.DEEPSEEK_API_KEY,
        model="deepseek-chat",
    )
    analyze_use_case = AnalyzeTranscriptUseCase(
        analyzer=_ds_analyzer, store=store_adapter
    )
    reconciler_adapter = DeepSeekReconcilerAdapter(
        api_key=settings.DEEPSEEK_API_KEY,
        model=settings.DEEPSEEK_RECONCILER_MODEL,
    )
    logger.info("[ai] DeepSeek analyzer + reconciler configured (no Anthropic key)")
else:
    logger.info("[ai] Transcript analysis disabled — set ANTHROPIC_API_KEY or DEEPSEEK_API_KEY")

if settings.QDRANT_URL:
    try:
        from .application.use_cases.search_transcripts import SearchTranscriptsUseCase
        from .infrastructure.qdrant_index import QdrantTranscriptIndex

        qdrant_adapter = QdrantTranscriptIndex(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
        search_use_case = SearchTranscriptsUseCase(index=qdrant_adapter)
        logger.info("[ai] Qdrant index configured (url=%s)", settings.QDRANT_URL)
    except Exception as e:
        logger.warning("[ai] Qdrant index disabled — connection failed: %s", e)
        qdrant_adapter = None
        search_use_case = None

# ── Use Case Wiring ─────────────────────────────────────────────────────
transcribe_use_case = TranscribeAudioUseCase(
    asr=asr_adapter,
    diarizer=diarizer_adapter,
    processor=processor_adapter,
    store=store_adapter,
    audio_files=audio_file_adapter,
    index=qdrant_adapter,
)
excerpt_use_case = DiarizeExcerptUseCase(
    diarizer=diarizer_adapter,
    audio_files=audio_file_adapter,
)
guided_transcribe_use_case = ReferenceGuidedTranscribeUseCase(
    asr=asr_adapter,
    diarizer=diarizer_adapter,
    processor=processor_adapter,
    store=store_adapter,
    audio_files=audio_file_adapter,
    ref_store=ref_store_adapter,
    reconciler=reconciler_adapter,
    narrative_store=narrative_store_adapter,
    index=qdrant_adapter,
)

# ── Router Injection ─────────────────────────────────────────────────────
init_diarization_router(excerpt_use_case, audio_file_adapter, settings.TRANSCRIPT_DIR)
init_transcription_router(transcribe_use_case, settings.ORIGINALS_DIR)
init_transcript_router(analyze_use_case, search_use_case, store_adapter, qdrant_adapter)

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
                model_manager.get_diarization_pipeline, settings.RESOLVED_HF_TOKEN
            )
            await asyncio.to_thread(model_manager.get_whisper_model, "small")
            log.info(f"Preload done in {time.time()-t:.2f}s")
        except Exception as e:
            log.warning(f"Preload skipped: {e}")

    asyncio.create_task(_preload())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
