---
name: awareness-ai-platform
description: "Awareness-AI platform engineering skill. Covers Anthropic Claude API integration, model selection and cost optimization, agent workspace configuration, Qdrant/Neo4j infrastructure, SSE streaming, step protocol observability, and Clean Architecture compliance. Use for: implementing features, configuring agents, switching models, debugging API issues, setting up infrastructure."
---

# Awareness-AI Platform Engineering Skill

## Anthropic Claude API Reference

### Available Models (March 2026)

| Model ID | Display Name | Best For | Input Cost | Output Cost | Max Output | Context |
|----------|-------------|----------|------------|-------------|------------|---------|
| `claude-opus-4-6` | Claude Opus 4.6 | Deep reasoning, architecture analysis | $15/1M | $75/1M | 32K | 200K |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 | Balanced reasoning + cost | $3/1M | $15/1M | 16K | 200K |
| `claude-sonnet-4-20250514` | Claude Sonnet 4 | Production default | $3/1M | $15/1M | 8K | 200K |
| `claude-haiku-4-5` | Claude Haiku 4.5 | Fast tasks, low cost | $0.80/1M | $4/1M | 8K | 200K |
| `claude-3-5-sonnet-20241022` | Claude 3.5 Sonnet | Legacy, still capable | $3/1M | $15/1M | 8K | 200K |

### Model Selection Guide

- **Architectural audits**: Use `claude-opus-4-6` with extended thinking — complex dependency analysis benefits from deep reasoning
- **General agent tasks**: Use `claude-sonnet-4-20250514` — best cost/quality ratio
- **Quick operations**: Use `claude-haiku-4-5` — 4x cheaper, suitable for simple file operations
- **Code generation**: Use `claude-sonnet-4-6` — latest Sonnet with improved code quality

### API Configuration

Config file: `awareness/config/config.toml`

```toml
[llm]
api_type = 'anthropic'
model = "claude-sonnet-4-20250514"
base_url = "https://api.anthropic.com"
api_key = "${ANTHROPIC_API_KEY}"
max_tokens = 6000
temperature = 0.15
```

Environment variable: Set `ANTHROPIC_API_KEY` in your shell or `.env` file.

### Switching Models at Runtime

The Awareness API provides model switching:

```
GET  /api/models/catalog    → List available models with pricing
GET  /api/models/current    → Show currently active model
POST /api/models/switch     → Switch to a different model
```

### API Features

#### Streaming
```python
# SSE streaming via the Messages API
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=6000,
    stream=True,
    messages=[{"role": "user", "content": prompt}]
)
```

#### Extended Thinking
```python
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 10000},
    messages=[...]
)
```

#### Tool Use
```python
tools = [{
    "name": "context_assemble",
    "description": "Semantic retrieval across all Qdrant collections + Neo4j graph expansion",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural language query"},
            "max_tokens": {"type": "integer", "default": 4000}
        },
        "required": ["query"]
    }
}]
```

#### Prompt Caching
Use `cache_control` to cache system prompts and reduce costs:
```python
system = [
    {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
]
```

#### Beta Features Available
- `prompt-caching-2024-07-31` — Cache prompts for 5min or 1hr
- `token-counting-2024-11-01` — Pre-count tokens before sending
- `extended-cache-ttl-2025-04-11` — Longer cache TTL
- `interleaved-thinking-2025-05-14` — Thinking interleaved with output
- `code-execution-2025-05-22` — Sandboxed code execution
- `context-management-2025-06-27` — Auto context management
- `fast-mode-2026-02-01` — Faster inference for latency-sensitive tasks

## Awareness API Server

### Architecture

```
awareness/
├── main.py              ← FastAPI app, all endpoints
├── app/
│   ├── agent/
│   │   ├── manus.py         ← Base agent class
│   │   ├── guided_agent.py  ← Pause/resume agent
│   │   └── auditor_agent.py ← Step protocol agent
│   ├── tool/
│   │   ├── base.py           ← BaseTool abstract class
│   │   ├── tool_collection.py
│   │   ├── context_assemble.py  ← Semantic retrieval
│   │   ├── qdrant_search.py     ← Vector search
│   │   ├── qdrant_ingest.py     ← Vector indexing
│   │   └── neo4j_query.py       ← Graph queries
│   ├── llm.py            ← LLM client singleton
│   ├── config.py          ← Config loader
│   └── qdrant/
│       └── services/
│           ├── embedding_service.py
│           └── qdrant_service.py
├── config/
│   └── config.toml        ← LLM + infra config (gitignored)
├── static/
│   ├── agent-workspace.html  ← Main workspace UI
│   ├── agent-manager.html    ← Agent CRUD UI
│   └── index.html            ← API console
└── docs/
    └── architecture/v2.0/    ← Architecture docs (HTML)
```

### SSE Event Types

| Event Type | Source | Description |
|-----------|--------|-------------|
| `step` | All agents | Step number + summary |
| `tool_call` | All agents | Tool name + arguments |
| `tool_result` | All agents | Tool output (truncated) |
| `thinking` | All agents | LLM reasoning text |
| `checkpoint` | All agents | Intermediate state |
| `awaiting_guidance` | Guided/Auditor | Paused for user input |
| `resumed` | Guided/Auditor | Resumed after guidance |
| `step_reasoning` | Auditor | Step protocol reasoning |
| `file_accessed` | Auditor | File access record |
| `data_consumed` | Auditor | Data consumption record |
| `step_outcome` | Auditor | Step completion with cost |
| `cost_warning` | Auditor | Cost threshold exceeded |
| `session_summary` | Auditor | Final session stats |
| `done` | All agents | Stream complete |
| `error` | All agents | Error occurred |

### Key Endpoints

```
POST /api/agent/stream         → General streaming
POST /api/guided/stream        → Guided mode streaming
POST /api/guided/pause         → Pause guided agent
POST /api/guided/resume        → Resume with guidance
POST /api/auditor/stream       → Auditor streaming
POST /api/auditor/mode         → Switch audit mode
GET  /api/agents/list          → List all agents
POST /api/agents/create        → Create agent
GET  /api/docs/tree            → Browse docs
GET  /api/file?path=...        → Serve file
GET  /api/models/catalog       → Model catalog
POST /api/models/switch        → Switch model
GET  /docs/v2/observability    → Agent observability architecture
GET  /docs/v2/implementation   → Argus implementation strategy
GET  /docs/v2/strategy         → Argus strategy overview
```

## Infrastructure Setup

### Qdrant
```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
# Verify: curl http://localhost:6333/collections
```

### Neo4j
```bash
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/yourpassword neo4j:5
# Verify: curl http://localhost:7474
```

### Environment Variables
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="yourpassword"
export QDRANT_URL="http://localhost:6333"
```

## Why Anthropic Claude

The Awareness-AI platform is built exclusively on the Anthropic Claude API. This is a deliberate architectural decision, not a limitation:

1. **Transparency** — Anthropic's Constitutional AI approach aligns with our "Accountable by Design" principle
2. **Security** — Anthropic's safety-first design philosophy matches our governance-grade requirements
3. **Reasoning Quality** — Claude's extended thinking capability is essential for architectural analysis
4. **Ethical Alignment** — Anthropic's commitment to beneficial AI mirrors our operational principles
5. **Tool Use** — Claude's native tool use is the foundation of our agent architecture
6. **Consistency** — Single-provider strategy ensures predictable behavior across all agents

This exclusivity enables deep integration: prompt caching, extended thinking, tool use patterns, and streaming are all optimized for the Claude API specifically.
