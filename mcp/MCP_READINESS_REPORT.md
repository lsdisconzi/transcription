# MCP Readiness Report

## Summary

- state: ready
- discovered_endpoints: 17
- mapped_endpoints: 17
- missing_endpoints: 0
- coverage_percent: 100.0

## Naming Checks

- tools_discovered: 17
- prefix_violations: 0
- snake_case_violations: 0

## Endpoint Coverage

- mapped: GET / -> pinocchio_health_root
- mapped: GET /api/diarization/models/whisper -> pinocchio_list_whisper_models
- mapped: GET /api/diarization/parameters -> pinocchio_list_parameter_definitions
- mapped: GET /api/transcripts -> pinocchio_list_transcripts
- mapped: GET /api/transcripts/status/{job_id} -> pinocchio_get_transcription_job
- mapped: GET /api/transcripts/stream/{job_id} -> pinocchio_stream_transcription_job
- mapped: GET /api/transcripts/{transcript_id} -> pinocchio_get_transcript
- mapped: GET /health -> pinocchio_health
- mapped: POST /api/diarization/excerpt -> pinocchio_diarize_excerpt
- mapped: POST /api/diarization/excerpt_by_path -> pinocchio_diarize_excerpt_by_path
- mapped: POST /api/diarization/transcribe -> pinocchio_transcribe_audio
- mapped: POST /api/diarization/transcribe/async -> pinocchio_transcribe_audio_async
- mapped: POST /api/transcripts/analyze -> pinocchio_analyze_transcript
- mapped: POST /api/transcripts/import -> pinocchio_import_transcripts
- mapped: POST /api/transcripts/index-all -> pinocchio_index_all_transcripts
- mapped: POST /api/transcripts/search -> pinocchio_search_transcripts
- mapped: POST /api/transcripts/{transcript_id}/index -> pinocchio_index_transcript
