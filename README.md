# SA-transcription — Chilean Spanish Audio Transcription & Diarization

High-accuracy transcription service combining **OpenAI Whisper** ASR with **Pyannote** speaker diarization, optimised for Chilean Spanish. Designed for legal and evidentiary audio analysis within the [Awareness-AI](https://github.com/awareness-ai) ecosystem.

## Features

- **Speaker diarization** — Identifies who speaks when using Pyannote 3.1
- **Whisper ASR** — Full Whisper model support (tiny → large-v3) with all decoding parameters
- **Chilean Spanish post-processing** — Regex rules for colloquial expressions ("po", "weón", "cachai", etc.)
- **Audio preprocessing** — Noise reduction, voice enhancement (band-pass 300-3400 Hz), loudness normalisation (LUFS), silence removal
- **AI transcript analysis** — Anthropic Claude integration for summaries, entity extraction, sentiment (optional)
- **Semantic search** — Qdrant vector store with sentence-transformers for transcript search (optional)
- **Clean Architecture** — Domain / Application / Infrastructure / Presentation layers with Protocol-based ports
- **Dual deployment** — FastAPI server or Runpod serverless handler

## Quick Start

### Prerequisites

- Python 3.12+
- FFmpeg (`brew install ffmpeg` / `apt install ffmpeg`)
- CUDA GPU (recommended for large-v3; CPU fallback supported)
- [HuggingFace token](https://huggingface.co/settings/tokens) with access to `pyannote/speaker-diarization-3.1`

### Local Development

```bash
# Clone and setup
git clone <repo-url> && cd sa-transcription
cp .env.example .env
# Edit .env with your HuggingFace/Pyannote tokens

# Install
python3.12 -m venv venv && source venv/bin/activate
pip install --upgrade pip setuptools
pip install -r requirements.txt

# Run
make run
# or: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | System info (GPU status, device) |
| `GET` | `/health` | Health check |
| `GET` | `/api/diarization/parameters` | Available parameters metadata |
| `GET` | `/api/diarization/models/whisper` | Available Whisper models |
| `POST` | `/api/diarization/transcribe` | Full transcription with diarization |
| `POST` | `/api/diarization/excerpt` | Diarize a time range (upload or path) |
| `POST` | `/api/diarization/excerpt_by_path` | Diarize excerpt by server path (JSON) |
| `GET` | `/api/transcripts` | List all transcript IDs |
| `GET` | `/api/transcripts/{id}` | Retrieve full transcript |
| `POST` | `/api/transcripts/analyze` | AI analysis via Claude (optional) |
| `POST` | `/api/transcripts/search` | Semantic search across transcripts (optional) |
| `POST` | `/api/transcripts/{id}/index` | Re-index single transcript into Qdrant |
| `POST` | `/api/transcripts/index-all` | Bulk re-index all transcripts |
| `GET` | `/api/transcripts/stream/{job_id}` | SSE progress streaming |

### Transcribe Example

```bash
curl -X POST http://localhost:8000/api/diarization/transcribe \
  -F "audio=@recording.wav" \
  -F "language=es-CL" \
  -F "model_size=large-v3" \
  -F "min_speakers=1" \
  -F "max_speakers=3"
```

## Architecture

```
src/
├── domain/              ← Entities, Ports (depends on nothing)
├── application/         ← Use cases, DTOs (depends on Domain)
├── infrastructure/      ← Adapters: Whisper, Pyannote, Pydub, JSON (implements Ports)
├── presentation/        ← FastAPI routers, middleware (depends on Application)
├── config.py            ← Environment settings
├── main.py              ← Composition root (DI wiring)
└── runpod_handler.py    ← Serverless bridge
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design document.

## Configuration

All settings are loaded from environment variables. See [.env.example](.env.example) for the full list.

| Variable | Description | Default |
|----------|-------------|---------|
| `PYANNOTE_AUTH_TOKEN` | HuggingFace token for Pyannote | — |
| `HF_TOKEN` | Canonical Hugging Face token env var | — |
| `HUGGINGFACE_HUB_TOKEN` | HuggingFace hub token | — |
| `AUDIO_DIR` | Processed audio output directory | `data/audio` |
| `ORIGINALS_DIR` | Original uploads directory | `data/originals` |
| `TRANSCRIPT_DIR` | JSON transcript storage | `data/transcripts` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000,http://localhost:8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ANTHROPIC_API_KEY` | Anthropic-compatible API key (enables AI analysis) | — |
| `ANTHROPIC_BASE_URL` | Anthropic-compatible base URL | `https://api.deepseek.com/anthropic` |
| `ANTHROPIC_MODEL` | Anthropic-compatible model for analysis | `deepseek-v4-pro` |
| `QDRANT_URL` | Qdrant server URL (enables semantic search) | `http://localhost:6333` |
| `QDRANT_API_KEY` | Qdrant API key (if secured) | — |

Pyannote token resolution order is:
`PYANNOTE_AUTH_TOKEN` → `HF_TOKEN` → `HUGGINGFACE_HUB_TOKEN` → `use_auth_token`.

## Testing

```bash
make test          # Run all tests
make test-unit     # Domain + application only
make lint          # Ruff linter
make typecheck     # Mypy type checking
```

## MCP Server (Transcription)

transcription now includes MCP servers that expose service capabilities as MCP tools
over stdio.

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run locally

```bash
make run-mcp-transcription
make run-mcp-transcripts
make run-mcp-meta
# or
python -m src.mcp.servers.transcription_server
python -m src.mcp.servers.transcripts_server
python -m src.mcp.servers.meta_server
```

### Tools exposed (transcription server)

- `transcribe_audio`
- `transcribe_audio_async`
- `get_transcription_job`
- `diarize_excerpt`

### Tools exposed (transcripts server)

- `list_transcripts`
- `get_transcript`
- `import_transcripts`
- `analyze_transcript`
- `search_transcripts`
- `index_transcript`
- `index_all_transcripts`

### Tools exposed (meta server)

- `health`
- `health_full`
- `list_parameter_definitions`
- `list_whisper_models`

### MCP client config example

```json
{
  "mcpServers": {
    "transcription-transcription": {
      "command": "python",
      "args": [
        "-m",
        "src.mcp.servers.transcription_server"
      ],
      "env": {
        "PYANNOTE_AUTH_TOKEN": "<your_token>",
        "HF_TOKEN": "<your_token>",
        "ORIGINALS_DIR": "data/originals",
        "TRANSCRIPT_DIR": "data/transcripts",
        "QDRANT_URL": "http://localhost:6333"
      }
    },
    "transcription-transcripts": {
      "command": "python",
      "args": [
        "-m",
        "src.mcp.servers.transcripts_server"
      ],
      "env": {
        "TRANSCRIPT_DIR": "data/transcripts",
        "ANTHROPIC_API_KEY": "<optional>",
        "DEEPSEEK_API_KEY": "<optional>",
        "QDRANT_URL": "http://localhost:6333"
      }
    },
    "transcription-meta": {
      "command": "python",
      "args": [
        "-m",
        "src.mcp.servers.meta_server"
      ],
      "env": {}
    }
  }
}
```

Full ready-to-use config file is available at `docs/mcp-servers.example.json`.

Input mode for `transcribe_audio` and `diarize_excerpt`:
- Use `file_path` for server-side files
- Or use `audio_base64` + optional `filename`

Both MCP servers and FastAPI now share the same dependency container in
`src/composition.py`, keeping service wiring consistent across interfaces.

## Security

- **No wildcard CORS** — explicit origins only
- **Path traversal prevention** — all file paths validated against allowed roots
- **No secrets in code** — all tokens via environment variables
- **`.gitignore` protection** — `.env`, data files, and caches excludedd

> **Token rotation required:** If you previously had tokens committed to git history, rotate them immediately on [HuggingFace](https://huggingface.co/settings/tokens) and [Runpod](https://www.runpod.io/console/user/settings).

## License

Private — Awareness-AI ecosystem. 
