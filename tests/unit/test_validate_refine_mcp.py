"""Smoke tests for the validate/refine MCP tool surface.

These tests bypass the FastMCP wire layer and call the underlying tool
functions directly through ``mcp._tool_manager``.  They confirm that the
``audit_transcript`` and ``patch_transcript_segments`` tools are registered
and route to the wired use cases / services produced by ``build_runtime``.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

# Ensure the runtime does not try to load torchaudio for these smoke tests.
os.environ.setdefault("ENABLE_ACOUSTIC_PROBES", "false")

from src.mcp.servers import transcripts_server as srv


def _call_tool(name: str, **kwargs):
    tool = srv.mcp._tool_manager.get_tool(name)
    assert tool is not None, f"tool {name} is not registered"
    result = tool.fn(**kwargs)
    if asyncio.iscoroutine(result):
        result = asyncio.run(result)
    return result


def _seed_transcript(tmp_path: Path) -> str:
    """Write a minimal Transcript JSON into the wired store and return its id."""
    store = srv._RUNTIME.store_adapter
    payload = {
        "transcript_id": "mcp_smoke",
        "segments": [
            {"index": 0, "speaker": "A", "start": 0.0, "end": 1.0, "text": "Hola"},
            {"index": 1, "speaker": "A", "start": 1.0, "end": 2.0, "text": " mundo."},
        ],
        "metadata": {},
        "source_file": "",
        "original_transcript_id": "mcp_smoke",
    }
    base = (
        getattr(store, "_directory", None)
        or getattr(store, "_dir", None)
        or getattr(store, "directory", None)
        or getattr(store, "base_dir", None)
        or tmp_path
    )
    target = Path(base) / "mcp_smoke.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")
    return "mcp_smoke"


def test_tools_are_registered():
    names = {t.name for t in srv.mcp._tool_manager.list_tools()}
    assert {"audit_transcript", "patch_transcript_segments", "validate_and_refine_transcript"} <= names


def test_audit_transcript_smoke(tmp_path):
    tid = _seed_transcript(tmp_path)
    out = _call_tool("audit_transcript", transcript_id=tid)
    assert isinstance(out, dict)
    assert out.get("transcript_id") == tid
    assert "anomalies" in out
    assert "counts_by_kind" in out


def test_patch_transcript_segments_smoke(tmp_path):
    tid = _seed_transcript(tmp_path)
    patches = [{"op": "replace_text", "segment_indices": [1], "new_text": "MUNDO"}]
    out = _call_tool(
        "patch_transcript_segments",
        transcript_id=tid,
        patches=patches,
        save_as_new_id=True,
    )
    assert isinstance(out, dict)
    assert out.get("transcript_id_in") == tid
    assert "_patched_" in out.get("transcript_id_out", "")
    assert out.get("patches_applied"), "expected at least one applied patch"
