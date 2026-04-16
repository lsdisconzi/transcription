---
description: Core coding guidelines for the Awareness-AI ecosystem. Loaded for all code generation, review, and modification tasks.
applyTo: '**/*.{py,js,ts,html,css,toml,yml,yaml,md}'
---

# Awareness-AI Coding Instructions

## 1. Security First

- **NEVER** hardcode API keys, passwords, or secrets in source files
- Use environment variables: `ANTHROPIC_API_KEY`, `NEO4J_PASSWORD`, `QDRANT_API_KEY`
- Config files with secrets (`config.toml`) are gitignored — use `config.example.toml` as template
- Validate file paths against allowed roots before serving
- Sanitize all user inputs at system boundaries

## 2. Python Standards

- Python 3.12+ with type hints on all signatures
- `async def` for all I/O-bound functions
- `pydantic.BaseModel` for all request/response schemas
- Logging: `from app.utils.logger import logger` — never use `print()`
- Config: `from app.config import config` singleton
- Imports: stdlib → third-party → local, separated by blank lines
- Error handling: catch specific exceptions, log with context

## 3. API Design

- FastAPI with Pydantic models for validation
- SSE (Server-Sent Events) for streaming responses
- Typed event format: `data: {"type": "event_type", ...}\n\n`
- HTTP status codes: 200 success, 400 validation, 403 access denied, 404 not found, 500 internal
- CORS configured per-origin, not wildcard

## 4. LLM Integration (Anthropic Claude)

- Provider: Anthropic only — chosen for transparency, security, and ethical alignment
- Models: `claude-opus-4-6` (premium), `claude-sonnet-4-20250514` (balanced), `claude-haiku-4-5` (fast)
- Always use the `LLM` class from `app.llm` — never instantiate API clients directly
- Token cost tracking: `$3/1M input`, `$15/1M output` (Sonnet); track per-step
- Extended thinking: enable for complex architectural analysis
- Tool use: define tools as `BaseTool` subclasses with `execute()` method

## 5. AI-First Retrieval Doctrine

When implementing any feature that needs codebase knowledge:
1. **First**: `context_assemble()` or `qdrant_search()` — semantic retrieval
2. **Second**: `neo4j_query()` — structural graph queries
3. **Third**: Direct file read — only when semantic score < 0.72
4. **After writes**: Always call `qdrant_ingest()` to keep the index current

## 6. Frontend Standards

- Design system: dark theme with branded CSS variables
- Colors: `--bg: #191917`, `--amber: #c4622d`, `--white: #ede8df`
- Fonts: Lora (headings), Inter (body), JetBrains Mono (code)
- All pages must include nav bar with Awareness-AI branding
- Use marked.js for markdown rendering, mammoth.js for DOCX preview
- SSE streaming with typed event handlers

## 7. Architecture Compliance

- Follow Clean Architecture: Domain → Application → Infrastructure → Presentation
- Dependencies flow inward only — never reference outer layers from inner ones
- Every agent step follows the Step Protocol: REASONING → TOOL_CALL → DATA_CONSUMED → OUTCOME
- New agent tools must extend `BaseTool` and be registered in `ToolCollection`
