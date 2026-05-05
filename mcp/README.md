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
- `transcription_transcribe_audio_guided`
- `transcription_transcribe_audio_guided_async`
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
- `transcription_list_projects`
- `transcription_get_project`
- `transcription_create_project`
- `transcription_update_project`
- `transcription_delete_project`
- `transcription_add_project_audio`
- `transcription_remove_project_audio`
- `transcription_add_project_context_doc`
- `transcription_remove_project_context_doc`
- `transcription_add_project_narrative`
- `transcription_list_references`
- `transcription_get_reference`
- `transcription_get_reference_manifest`
- `transcription_get_reference_narratives`
- `transcription_upload_reference`
- `transcription_link_reference`

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

Important:
- Start only one server per terminal session.
- Once started, do not type shell commands into that same terminal; stdio is reserved for MCP JSON-RPC messages.
- If you need to start another server, open a new terminal tab/window.
- Stop a running server with `Ctrl+C`.

Notes on warnings:
- `SyntaxWarning: invalid escape sequence` from packages like `pydub` or `pyannote` is non-fatal and does not prevent MCP startup.
- If needed, suppress these warnings with `PYTHONWARNINGS=ignore::SyntaxWarning`.
