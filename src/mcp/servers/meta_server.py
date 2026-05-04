"""transcription MCP server: health and model/parameter metadata tools.

Launch with:
    python -m src.mcp.servers.meta_server
"""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import torch
from mcp.server.fastmcp import FastMCP
from whisper import available_models

from src.config import settings
from src.infrastructure.narrative_store_adapter import NarrativeStoreAdapter
from src.infrastructure.project_store_adapter import ProjectStoreAdapter
from src.infrastructure.reference_store_adapter import ReferenceStoreAdapter

mcp = FastMCP("transcription-meta")

_project_store = ProjectStoreAdapter(settings.PROJECTS_DIR)
_ref_store = ReferenceStoreAdapter(settings.REFERENCE_DIR)
_narrative_store = NarrativeStoreAdapter(settings.NARRATIVE_DIR)


@mcp.tool()
def health() -> dict[str, Any]:
    """Return basic service health metadata."""
    return {
        "status": "ok",
        "service": "transcription",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@mcp.tool()
def health_full() -> dict[str, Any]:
    """Return extended runtime health metadata."""
    return {
        "status": "ok",
        "service": "transcription",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "torch_device": settings.TORCH_DEVICE,
        "torch_float": settings.TORCH_FLOAT,
        "cuda_available": torch.cuda.is_available(),
    }


@mcp.tool()
def list_parameter_definitions() -> dict[str, Any]:
    """Return full transcription parameter metadata."""
    return {
        "general": {
            "language": "Input language locale (maps to Whisper language code). Ex: es-CL, en, pt-BR.",
            "model_size": "Whisper model variant. Larger = better quality, slower & more RAM.",
            "min_speakers": "Lower bound for expected speakers (diarization constraint).",
            "max_speakers": "Upper bound for expected speakers (diarization constraint).",
            "vad_threshold": "Voice activity probability threshold (lower = more segments, higher = stricter).",
        },
        "preprocessing": {
            "noise_reduce": "Apply spectral noise reduction (slow for long audio).",
            "reduction_db": "Approximate aggressiveness (0-40). Higher may introduce artifacts.",
            "voice_enhance": "Apply band-pass filtering + dynamic range compression.",
            "apply_gain": "Loudness normalization toward target_lufs.",
            "target_lufs": "Target loudness (LUFS). Typical podcast: -16 (stereo) / -19 (mono).",
            "remove_silence": "Remove detected silence segments before diarization.",
            "silence_thresh": "Silence threshold dBFS (e.g. -45). Higher (less negative) removes more.",
            "min_silence_len": "Minimum silence length (ms) to qualify for removal.",
        },
        "whisper_decoding": {
            "beam_size": "Beam search width (larger = better accuracy, slower).",
            "best_of": "Number of sampled candidates when not using temperature=0.",
            "whisper_temp": "Starting sampling temperature. 0 = deterministic.",
            "temperature_increment_on_fallback": "Temperature added on each fallback attempt.",
            "compression_ratio_threshold": "Abort & retry if gzip ratio exceeds this.",
            "logprob_threshold": "Abort & retry if avg log-prob below this.",
            "no_speech_threshold": "If no-speech probability exceeds this -> treat as silence.",
            "condition_on_previous_text": "Feed previous segment text as context.",
            "initial_prompt": "Optional priming text or domain vocabulary.",
            "length_penalty": "Adjust preference for longer/shorter outputs in beam search.",
            "patience": "Beam search termination patience.",
            "suppress_blank": "Suppress blank tokens.",
            "suppress_tokens": "Comma list of token IDs to suppress (-1 = library default).",
            "word_timestamps": "Enable per-word timestamps (slower).",
        },
        "control": {
            "keep_cache": "Keep models in memory after request for reuse (faster subsequent calls).",
        },
    }


@mcp.tool()
def list_whisper_models() -> dict[str, Any]:
    """Return locally available Whisper model names."""
    return {"available_models": available_models()}


# ── Project / Event Journey tools ────────────────────────────────────────


@mcp.tool()
def list_projects() -> dict[str, Any]:
    """List all transcription projects (event journeys) on disk."""
    projects = _project_store.list_projects()
    return {
        "count": len(projects),
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "language": p.language,
                "location": p.location,
                "n_audios": len(p.audios),
                "n_context_docs": len(p.context_docs),
                "n_narratives": len(p.narrative_ids),
                "qdrant_filter_tag": p.qdrant_filter_tag,
                "updated_at": p.updated_at,
            }
            for p in projects
        ],
    }


@mcp.tool()
def get_project(project_id: str) -> dict[str, Any]:
    """Return the full project record (audios, references, narratives, context docs)."""
    project = _project_store.load(project_id)
    if not project:
        return {"error": f"project {project_id} not found"}
    data = asdict(project)
    # Augment with reference manifest summaries
    summaries = []
    for cn in project.canonical_names():
        m = _ref_store.load_manifest(cn)
        summaries.append({
            "canonical_name": cn,
            "has_manifest": m is not None,
            "n_references": len([v for v in m.versions if v.type == "reference"]) if m else 0,
            "n_versions": len(m.versions) if m else 0,
        })
    data["references_summary"] = summaries
    return data


@mcp.tool()
def list_project_references(project_id: str) -> dict[str, Any]:
    """For each audio in a project, list its reference versions."""
    project = _project_store.load(project_id)
    if not project:
        return {"error": f"project {project_id} not found"}
    out = []
    for audio in project.audios:
        refs = _ref_store.load_references(audio.canonical_name)
        out.append({
            "canonical_name": audio.canonical_name,
            "audio_path": audio.audio_path,
            "n_references": len(refs),
            "references": [
                {
                    "title": r.title,
                    "source": r.source,
                    "quality_score": r.quality_score,
                    "n_segments": len(r.content),
                }
                for r in refs
            ],
        })
    return {"project_id": project_id, "audios": out}


@mcp.tool()
def read_project_context_doc(project_id: str, path: str, max_chars: int = 12000) -> dict[str, Any]:
    """Read a context document attached to a project (limited to attached paths).

    The agent must pass a ``path`` that is registered as one of the project's
    context_docs — this prevents arbitrary filesystem reads.
    """
    project = _project_store.load(project_id)
    if not project:
        return {"error": f"project {project_id} not found"}
    allowed = {d.path for d in project.context_docs}
    if path not in allowed:
        return {"error": "path not attached to this project", "attached": sorted(allowed)}
    if not os.path.isfile(path):
        return {"error": f"file missing on disk: {path}"}
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read(max_chars + 1)
    except OSError as exc:
        return {"error": f"read failed: {exc}"}
    truncated = len(text) > max_chars
    return {
        "path": path,
        "truncated": truncated,
        "content": text[:max_chars],
    }


@mcp.tool()
def list_project_narratives(project_id: str) -> dict[str, Any]:
    """List narratives linked to a project (resolves via narrative store)."""
    project = _project_store.load(project_id)
    if not project:
        return {"error": f"project {project_id} not found"}
    out = []
    for cn in project.canonical_names():
        for n in _narrative_store.load_narratives(cn):
            out.append({
                "audio_id": n.audio_id,
                "title": n.title,
                "timeline_time": n.timeline_time,
                "source_file": n.source_file,
                "preview": n.text[:300] + ("..." if len(n.text) > 300 else ""),
            })
    return {"project_id": project_id, "count": len(out), "narratives": out}


def main() -> None:
    """Entrypoint for stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
