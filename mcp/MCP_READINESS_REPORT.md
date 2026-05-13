# MCP Readiness Report

## Summary

- state: ready
- discovered_endpoints: 38
- mapped_endpoints: 38
- missing_endpoints: 0
- coverage_percent: 100.0

## Naming Checks

- tools_discovered: 38
- prefix_violations: 0
- snake_case_violations: 0

## Endpoint Coverage

- mapped: DELETE /api/projects/{project_id} -> transcription_delete_project
- mapped: DELETE /api/projects/{project_id}/audios/{canonical_name} -> transcription_remove_project_audio
- mapped: DELETE /api/projects/{project_id}/context_docs -> transcription_remove_project_context_doc
- mapped: GET / -> transcription_health_root
- mapped: GET /api/diarization/models/whisper -> transcription_list_whisper_models
- mapped: GET /api/diarization/parameters -> transcription_list_parameter_definitions
- mapped: GET /api/projects -> transcription_list_projects
- mapped: GET /api/projects/{project_id} -> transcription_get_project
- mapped: GET /api/references -> transcription_list_references
- mapped: GET /api/references/{canonical_name} -> transcription_get_reference
- mapped: GET /api/references/{canonical_name}/manifest -> transcription_get_reference_manifest
- mapped: GET /api/references/{canonical_name}/narratives -> transcription_get_reference_narratives
- mapped: GET /api/transcripts -> transcription_list_transcripts
- mapped: GET /api/transcripts/status/{job_id} -> transcription_get_transcription_job
- mapped: GET /api/transcripts/stream/{job_id} -> transcription_stream_transcription_job
- mapped: GET /api/transcripts/{transcript_id} -> transcription_get_transcript
- mapped: GET /health -> transcription_health
- mapped: PATCH /api/projects/{project_id} -> transcription_update_project
- mapped: POST /api/diarization/excerpt -> transcription_diarize_excerpt
- mapped: POST /api/diarization/excerpt_by_path -> transcription_diarize_excerpt_by_path
- mapped: POST /api/diarization/transcribe -> transcription_transcribe_audio
- mapped: POST /api/diarization/transcribe/async -> transcription_transcribe_audio_async
- mapped: POST /api/diarization/transcribe/guided -> transcription_transcribe_audio_guided
- mapped: POST /api/diarization/transcribe/guided/async -> transcription_transcribe_audio_guided_async
- mapped: POST /api/projects -> transcription_create_project
- mapped: POST /api/projects/{project_id}/audios -> transcription_add_project_audio
- mapped: POST /api/projects/{project_id}/context_docs -> transcription_add_project_context_doc
- mapped: POST /api/projects/{project_id}/narratives -> transcription_add_project_narrative
- mapped: POST /api/references/{canonical_name}/link -> transcription_link_reference
- mapped: POST /api/references/{canonical_name}/upload -> transcription_upload_reference
- mapped: POST /api/transcripts/analyze -> transcription_analyze_transcript
- mapped: POST /api/transcripts/import -> transcription_import_transcripts
- mapped: POST /api/transcripts/index-all -> transcription_index_all_transcripts
- mapped: POST /api/transcripts/search -> transcription_search_transcripts
- mapped: POST /api/transcripts/{transcript_id}/audit -> transcription_audit_transcript
- mapped: POST /api/transcripts/{transcript_id}/index -> transcription_index_transcript
- mapped: POST /api/transcripts/{transcript_id}/patch -> transcription_patch_transcript_segments
- mapped: POST /api/transcripts/{transcript_id}/refine -> transcription_refine_transcript
