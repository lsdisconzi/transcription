# Pinocchio MCP Bootstrap

This directory provides a bootstrap MCP surface for this project using the
`python-fastmcp-multi` pattern.

## Servers

- `pinocchio-transcription` → `mcp/servers/transcription_server.py`
- `pinocchio-transcripts` → `mcp/servers/transcripts_server.py`
- `pinocchio-meta` → `mcp/servers/meta_server.py`

## Tool Inventory

### pinocchio-transcription

- `pinocchio_transcribe_audio`
- `pinocchio_transcribe_audio_async`
- `pinocchio_get_transcription_job`
- `pinocchio_stream_transcription_job`
- `pinocchio_diarize_excerpt`
- `pinocchio_diarize_excerpt_by_path`

### pinocchio-transcripts

- `pinocchio_list_transcripts`
- `pinocchio_get_transcript`
- `pinocchio_import_transcripts`
- `pinocchio_analyze_transcript`
- `pinocchio_search_transcripts`
- `pinocchio_index_transcript`
- `pinocchio_index_all_transcripts`

### pinocchio-meta

- `pinocchio_health_root`
- `pinocchio_health`
- `pinocchio_list_parameter_definitions`
- `pinocchio_list_whisper_models`

## Generate Readiness Report

```bash
python mcp/generate_readiness_report.py
```

## Syntax Check

```bash
python -m py_compile mcp/servers/*.py mcp/generate_readiness_report.py
```

## Startup (Stdio)

```bash
python mcp/servers/meta_server.py
python mcp/servers/transcription_server.py
python mcp/servers/transcripts_server.py
```
