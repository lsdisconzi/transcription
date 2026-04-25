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

- mapped: GET / -> transcription_health_root
- mapped: GET /api/diarization/models/whisper -> transcription_list_whisper_models
- mapped: GET /api/diarization/parameters -> transcription_list_parameter_definitions
- mapped: GET /api/transcripts -> transcription_list_transcripts
- mapped: GET /api/transcripts/status/{job_id} -> transcription_get_transcription_job
- mapped: GET /api/transcripts/stream/{job_id} -> transcription_stream_transcription_job
- mapped: GET /api/transcripts/{transcript_id} -> transcription_get_transcript
- mapped: GET /health -> transcription_health
- mapped: POST /api/diarization/excerpt -> transcription_diarize_excerpt
- mapped: POST /api/diarization/excerpt_by_path -> transcription_diarize_excerpt_by_path
- mapped: POST /api/diarization/transcribe -> transcription_transcribe_audio
- mapped: POST /api/diarization/transcribe/async -> transcription_transcribe_audio_async
- mapped: POST /api/transcripts/analyze -> transcription_analyze_transcript
- mapped: POST /api/transcripts/import -> transcription_import_transcripts
- mapped: POST /api/transcripts/index-all -> transcription_index_all_transcripts
- mapped: POST /api/transcripts/search -> transcription_search_transcripts
- mapped: POST /api/transcripts/{transcript_id}/index -> transcription_index_transcript
