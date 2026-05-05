"""transcription MCP metadata server (bootstrap standard).

Launch with:
    python mcp/servers/meta_server.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mcp.servers import meta_server as src_meta

mcp = FastMCP("transcription-meta")


@mcp.tool()
def transcription_health_root() -> dict[str, Any]:
    """Return health payload mapped to GET /."""
    return src_meta.health()


@mcp.tool()
def transcription_health() -> dict[str, Any]:
    """Return extended health payload mapped to GET /health."""
    return src_meta.health_full()


@mcp.tool()
def transcription_list_parameter_definitions() -> dict[str, Any]:
    """Return transcription parameter metadata."""
    return src_meta.list_parameter_definitions()


@mcp.tool()
def transcription_list_whisper_models() -> dict[str, Any]:
    """Return available Whisper model names."""
    return src_meta.list_whisper_models()


@mcp.tool()
def transcription_list_projects() -> dict[str, Any]:
    """Return all projects mapped to GET /api/projects."""
    return src_meta.list_projects_api()


@mcp.tool()
def transcription_get_project(project_id: str) -> dict[str, Any]:
    """Return one project mapped to GET /api/projects/{project_id}."""
    return src_meta.get_project_api(project_id)


@mcp.tool()
def transcription_create_project(
    name: str,
    project_id: str | None = None,
    description: str = "",
    language: str = "es",
    location: str = "",
    audios: list[dict[str, Any]] | None = None,
    narrative_ids: list[str] | None = None,
    context_docs: list[dict[str, Any]] | None = None,
    qdrant_filter_tag: str = "",
) -> dict[str, Any]:
    """Create project mapped to POST /api/projects."""
    return src_meta.create_project_api(
        name=name,
        project_id=project_id,
        description=description,
        language=language,
        location=location,
        audios=audios,
        narrative_ids=narrative_ids,
        context_docs=context_docs,
        qdrant_filter_tag=qdrant_filter_tag,
    )


@mcp.tool()
def transcription_update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    language: str | None = None,
    location: str | None = None,
    qdrant_filter_tag: str | None = None,
) -> dict[str, Any]:
    """Update project mapped to PATCH /api/projects/{project_id}."""
    return src_meta.update_project_api(
        project_id=project_id,
        name=name,
        description=description,
        language=language,
        location=location,
        qdrant_filter_tag=qdrant_filter_tag,
    )


@mcp.tool()
def transcription_delete_project(project_id: str) -> dict[str, Any]:
    """Delete project mapped to DELETE /api/projects/{project_id}."""
    return src_meta.delete_project_api(project_id)


@mcp.tool()
def transcription_add_project_audio(
    project_id: str,
    canonical_name: str,
    audio_path: str = "",
    title: str = "",
    recording_datetime: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """Attach project audio mapped to POST /api/projects/{project_id}/audios."""
    return src_meta.add_project_audio_api(
        project_id=project_id,
        canonical_name=canonical_name,
        audio_path=audio_path,
        title=title,
        recording_datetime=recording_datetime,
        notes=notes,
    )


@mcp.tool()
def transcription_remove_project_audio(project_id: str, canonical_name: str) -> dict[str, Any]:
    """Remove project audio mapped to DELETE /api/projects/{project_id}/audios/{canonical_name}."""
    return src_meta.remove_project_audio_api(project_id=project_id, canonical_name=canonical_name)


@mcp.tool()
def transcription_add_project_context_doc(
    project_id: str,
    path: str,
    title: str = "",
    kind: str = "report",
    notes: str = "",
) -> dict[str, Any]:
    """Attach context doc mapped to POST /api/projects/{project_id}/context_docs."""
    return src_meta.add_project_context_doc_api(
        project_id=project_id,
        path=path,
        title=title,
        kind=kind,
        notes=notes,
    )


@mcp.tool()
def transcription_remove_project_context_doc(project_id: str, path: str) -> dict[str, Any]:
    """Detach context doc mapped to DELETE /api/projects/{project_id}/context_docs."""
    return src_meta.remove_project_context_doc_api(project_id=project_id, path=path)


@mcp.tool()
def transcription_add_project_narrative(project_id: str, narrative_id: str) -> dict[str, Any]:
    """Attach narrative mapped to POST /api/projects/{project_id}/narratives."""
    return src_meta.add_project_narrative_api(project_id=project_id, narrative_id=narrative_id)


@mcp.tool()
def transcription_list_references() -> dict[str, Any]:
    """List reference canonical names mapped to GET /api/references."""
    return src_meta.list_references_api()


@mcp.tool()
def transcription_get_reference(canonical_name: str) -> dict[str, Any]:
    """Get references mapped to GET /api/references/{canonical_name}."""
    return src_meta.get_reference_api(canonical_name)


@mcp.tool()
def transcription_get_reference_manifest(canonical_name: str) -> dict[str, Any]:
    """Get manifest mapped to GET /api/references/{canonical_name}/manifest."""
    return src_meta.get_reference_manifest_api(canonical_name)


@mcp.tool()
def transcription_get_reference_narratives(canonical_name: str) -> dict[str, Any]:
    """Get narratives mapped to GET /api/references/{canonical_name}/narratives."""
    return src_meta.get_reference_narratives_api(canonical_name)


@mcp.tool()
def transcription_upload_reference(
    canonical_name: str,
    source_path: str,
    quality_score: float = 0.9,
    source: str = "manual_correction",
    notes: str = "",
    filename: str | None = None,
) -> dict[str, Any]:
    """Upload reference mapped to POST /api/references/{canonical_name}/upload."""
    return src_meta.upload_reference_api(
        canonical_name=canonical_name,
        source_path=source_path,
        quality_score=quality_score,
        source=source,
        notes=notes,
        filename=filename,
    )


@mcp.tool()
def transcription_link_reference(
    canonical_name: str,
    source_path: str,
    quality_score: float = 0.9,
    source: str = "linked",
    notes: str = "",
    copy: bool = False,
) -> dict[str, Any]:
    """Link reference mapped to POST /api/references/{canonical_name}/link."""
    return src_meta.link_reference_api(
        canonical_name=canonical_name,
        source_path=source_path,
        quality_score=quality_score,
        source=source,
        notes=notes,
        copy=copy,
    )


def main() -> None:
    """Entrypoint for stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
