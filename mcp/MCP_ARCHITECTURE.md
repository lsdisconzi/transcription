# Pinocchio MCP Architecture

This folder follows the canonical MCP architecture standard at:
`/Users/leandrodisconzi/2026/garage-main/mcp/MCP_ARCHITECTURE.md`.

## Pattern

- Pattern: `python-fastmcp-multi`
- Servers live under `mcp/servers/`
- Transport: stdio
- Runtime style: direct invocation via existing project composition/use cases

## Servers

- `mcp/servers/transcription_server.py` (`pinocchio-transcription`)
- `mcp/servers/transcripts_server.py` (`pinocchio-transcripts`)
- `mcp/servers/meta_server.py` (`pinocchio-meta`)

## Naming Rules

- Tool names are snake_case
- Tool names are prefixed with `pinocchio_`

## Safety Rules

- No hardcoded secrets
- Runtime config provided through environment variables in MCP client config
- No destructive delete/reset operations are exposed in this bootstrap set

## Coverage Strategy

- Endpoint discovery source: `src/presentation/routers/*.py`
- MCP tool discovery source: `mcp/servers/*.py`
- Mapping source of truth: `mcp/generate_readiness_report.py`

## Validation

- Syntax check:
  - `python -m py_compile mcp/servers/*.py mcp/generate_readiness_report.py`
- Readiness generation:
  - `python mcp/generate_readiness_report.py`
- Startup check:
  - `python mcp/servers/meta_server.py`
  - `python mcp/servers/transcription_server.py`
  - `python mcp/servers/transcripts_server.py`
