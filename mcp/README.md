# transcription MCP Bootstrap

This directory provides a bootstrap MCP surface for this project using the
`python-fastmcp-multi` pattern.

## Servers

- `transcription-transcription` → `mcp/servers/transcription_server.py`
- `transcription-transcripts` → `mcp/servers/transcripts_server.py`
- `transcription-meta` → `mcp/servers/meta_server.py`

## Tool Inventory

### transcription-transcription

- `transcription_transcribe_audio`
- `transcription_transcribe_audio_async`
- `transcription_get_transcription_job`
- `transcription_stream_transcription_job`
- `transcription_diarize_excerpt`
- `transcription_diarize_excerpt_by_path`

### transcription-transcripts

- `transcription_list_transcripts`
- `transcription_get_transcript`
- `transcription_import_transcripts`
- `transcription_analyze_transcript`
- `transcription_search_transcripts`
- `transcription_index_transcript`
- `transcription_index_all_transcripts`

### transcription-meta

- `transcription_health_root`
- `transcription_health`
- `transcription_list_parameter_definitions`
- `transcription_list_whisper_models`

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
