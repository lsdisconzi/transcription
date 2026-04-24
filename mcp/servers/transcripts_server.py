"""Pinocchio MCP transcripts server (bootstrap standard).

Launch with:
    python mcp/servers/transcripts_server.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mcp.servers import transcripts_server as src_transcripts

mcp = FastMCP("pinocchio-transcripts")


@mcp.tool()
def pinocchio_list_transcripts() -> dict[str, Any]:
    """Return all transcript ids."""
    return src_transcripts.list_transcripts()


@mcp.tool()
def pinocchio_get_transcript(transcript_id: str) -> dict[str, Any]:
    """Load one transcript by id."""
    return src_transcripts.get_transcript(transcript_id)


@mcp.tool()
def pinocchio_import_transcripts(
    runs: list[dict[str, Any]],
    overwrite: bool = False,
    rename_by_filename: bool = True,
) -> dict[str, Any]:
    """Import transcript runs into persistent transcript storage."""
    return src_transcripts.import_transcripts(
        runs=runs,
        overwrite=overwrite,
        rename_by_filename=rename_by_filename,
    )


@mcp.tool()
async def pinocchio_analyze_transcript(transcript_id: str, instructions: str = "") -> dict[str, Any]:
    """Run transcript analysis for one transcript id."""
    return await src_transcripts.analyze_transcript(
        transcript_id=transcript_id,
        instructions=instructions,
    )


@mcp.tool()
async def pinocchio_search_transcripts(query: str, limit: int = 5) -> dict[str, Any]:
    """Run semantic search across indexed transcript segments."""
    return await src_transcripts.search_transcripts(query=query, limit=limit)


@mcp.tool()
async def pinocchio_index_transcript(transcript_id: str) -> dict[str, Any]:
    """Index one transcript into Qdrant."""
    return await src_transcripts.index_transcript(transcript_id)


@mcp.tool()
async def pinocchio_index_all_transcripts() -> dict[str, Any]:
    """Index all transcripts into Qdrant."""
    return await src_transcripts.index_all_transcripts()


def main() -> None:
    """Entrypoint for stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
