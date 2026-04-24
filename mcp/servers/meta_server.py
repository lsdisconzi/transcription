"""Pinocchio MCP metadata server (bootstrap standard).

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

mcp = FastMCP("pinocchio-meta")


@mcp.tool()
def pinocchio_health_root() -> dict[str, Any]:
    """Return health payload mapped to GET /."""
    return src_meta.health()


@mcp.tool()
def pinocchio_health() -> dict[str, Any]:
    """Return extended health payload mapped to GET /health."""
    return src_meta.health_full()


@mcp.tool()
def pinocchio_list_parameter_definitions() -> dict[str, Any]:
    """Return transcription parameter metadata."""
    return src_meta.list_parameter_definitions()


@mcp.tool()
def pinocchio_list_whisper_models() -> dict[str, Any]:
    """Return available Whisper model names."""
    return src_meta.list_whisper_models()


def main() -> None:
    """Entrypoint for stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
