# Awareness-AI — GitHub Copilot Repository Instructions
# This file is automatically included in every Copilot chat in this repository.
# Ontology v2.4 · Accountable by Design · AI-First · 2026
# ─────────────────────────────────────────────────────────────────────────────

## What This Repository Is

This is the **Awareness-AI** operational intelligence platform — a Python/FastAPI
backend with a structured AI agent pipeline, semantic retrieval (Qdrant), graph
reasoning (Neo4j), and full step-level observability.

This is NOT a general-purpose web application. Every architectural decision serves
one goal: **AI-native operational intelligence built on Clean Architecture.**

---

## Repository Structure

```
awareness/
├── app/
│   ├── agent/
│   │   ├── auditor_agent.py       ← AuditorAgent — architectural audit agent
│   │   ├── step_protocol.py       ← StepProtocolTracker — token/cost/SSE events
│   │   ├── manus.py               ← Manus base agent
│   │   ├── base.py                ← BaseAgent
│   │   └── guided_agent.py        ← GuidedAgent (parent of AuditorAgent)
│   └── tool/
│       ├── context_assemble.py    ← Tier-1: Qdrant + Neo4j full pipeline
│       ├── qdrant_ingest.py       ← Index files into Qdrant vector store
│       ├── neo4j_query.py         ← 10 named Cypher templates
│       └── __init__.py            ← Exports all tools
├── static/
│   ├── agent-workspace.html       ← Main UI — SSE streaming, cost badge, audit log
│   └── index-enhanced.html        ← Test/debug interface
├── main.py                        ← FastAPI app — all API endpoints
└── _shared/
    ├── agents/                    ← Agent definition files (.md)
    ├── docs/                      ← Architecture docs, product vision
    ├── ontology/                  ← Ontology v2.4 spec
    └── corpus/                    ← Shared data (law, transcripts, media)
```

---

## AI Provider — Anthropic Claude API

This project uses **Anthropic Claude exclusively** as its LLM provider.

**Why Anthropic only:**
- Constitutional AI and safety-by-design align with Awareness-AI's accountability principles
- Transparent pricing model matches our cost-visibility architecture
- Extended thinking capability enables the deep architectural reasoning this agent requires
- API reliability and documented behavior support production-grade agent pipelines

**Model selection guide (see MODEL_GUIDE.md for full details):**

| Model | Use Case | Input cost | Output cost |
|-------|----------|-----------|-------------|
| `claude-opus-4-5` | Complex architectural reasoning, multi-step audits | $15/M | $75/M |
| `claude-sonnet-4-5` | **Default** — balanced reasoning + speed | $3/M | $15/M |
| `claude-haiku-4-5` | Fast lookups, simple queries, cost-sensitive runs | $0.80/M | $4/M |

**The model dropdown in agent-workspace.html must always show:**
1. Which model is currently active
2. The per-step estimated cost in real-time
3. A one-click model switcher with cost previews

**API client pattern:**
```python
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Standard call
response = client.messages.create(
    model="claude-sonnet-4-5",   # or claude-opus-4-5 / claude-haiku-4-5
    max_tokens=8192,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_prompt}]
)

# Extended thinking (for complex audit steps only — Opus or Sonnet)
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 10000},
    messages=[...]
)
```

---

## The AI-First Law

**The single most important rule in this codebase:**

```python
# WRONG — never do this first
content = open("some_file.py").read()

# RIGHT — always do this first
results = context_assemble_tool.run(query="what does some_file.py contain")
# Only read the file directly if results.relevance_score < 0.72
```

Every agent action must attempt semantic retrieval before direct file access.
Score threshold: **0.72** (below = escalate to file read with documented reason).

This applies to Copilot suggestions too. When generating agent code:
- Always show `context_assemble` or `qdrant_search` as the first tool call
- Never generate code that opens files without a preceding semantic query
- Always include `qdrant_ingest(file_path)` after any file write operation

---

## Architecture Rules — Enforced

### Clean Architecture Dependency Direction
```
Presentation → Application → Domain ← Infrastructure
```

**Never generate code that violates these rules:**
- Domain classes must have ZERO imports from Infrastructure, FastAPI, or SQLAlchemy
- Application services must not import from Presentation (FastAPI routers)
- Infrastructure classes implement Domain interfaces — never the reverse

### SSE Event Protocol
Every agent step must emit these events in order:
```python
# 1. Step begins
tracker.emit_step_reasoning(step, rationale, next_action)

# 2. Tool called — file access recorded if applicable
tracker.emit_file_accessed(step, file_path, access_type, bytes_read)

# 3. Data used from retrieval
tracker.emit_data_consumed(step, file_path, excerpt, tokens_used, relevance_score)

# 4. Step completes
tracker.emit_step_outcome(step, summary, tokens_in, tokens_out, cost_usd)
```

**Never generate agent step code that skips `emit_step_outcome`.**
This breaks the cost badge and session total.

### Token Budget
- Maximum context per agent step: **4,096 tokens**
- If `context_assemble` returns more: sort by relevance_score, trim lowest
- Always include `tokens_in`, `tokens_out`, `cost_usd` in step outcomes

---

## API Endpoints

### Auditor Agent
```
POST /api/auditor/stream   ← SSE streaming with full step-protocol traceability
POST /api/auditor/pause    ← Pause between steps
POST /api/auditor/resume   ← Resume with optional guidance
POST /api/auditor/stop     ← Halt execution
POST /api/auditor/mode     ← Switch: audit / proposal / migration / enforcement
```

### General Agent
```
POST /api/agent/stream     ← SSE streaming (general purpose)
POST /api/agent/stop       ← Stop
POST /api/guided/stream    ← Guided SSE streaming
POST /api/guided/resume    ← Resume guided with input
POST /api/guided/stop      ← Stop guided
```

### Request format (all streaming endpoints)
```json
{ "userPrompt": "..." }
```

### SSE Event types emitted
```
step · tool_call · tool_result · thinking · checkpoint · awaiting_guidance
resumed · stopped · done · error · file_accessed · data_consumed
step_reasoning · step_outcome
```

---

## Tool Implementations

### ContextAssembleTool (`app/tool/context_assemble.py`)
Multi-collection Qdrant search + Neo4j graph expansion, merged and token-budgeted.
```python
tool = ContextAssembleTool()
result = await tool.execute(query="...", max_tokens=4000)
# result.context — assembled text
# result.sources — [{ file_path, score }]
# result.estimated_tokens — token count
```

### QdrantIngestTool (`app/tool/qdrant_ingest.py`)
Chunks a file, embeds it, upserts into the correct collection.
```python
tool = QdrantIngestTool()
result = await tool.execute(file_path="...", collection="awa_code")
# Auto-detects collection from file extension if not specified
```

### Neo4jQueryTool (`app/tool/neo4j_query.py`)
10 named Cypher templates for structural graph queries.
```python
tool = Neo4jQueryTool()
result = await tool.execute(template="file_dependencies", params={"targetPath": "..."})
```

Templates: `files_by_entity`, `file_dependencies`, `file_dependents`,
`decision_chain`, `recently_accessed`, `expand_chunks`, `invariant_check`,
`register_file`, `register_step`, `record_file_access`

### StepProtocolTracker (`app/agent/step_protocol.py`)
Per-step token/cost tracking + SSE event emission.
```python
tracker = StepProtocolTracker(session_id="...", response_stream=res)
tracker.begin_step(step_num, rationale)
tracker.record_tokens(tokens_in, tokens_out, model="claude-sonnet-4-5")
tracker.emit_step_outcome(step_num, summary)
```

---

## Qdrant Collections

| Collection | Content | Auto-ingest trigger |
|-----------|---------|-------------------|
| `awa_documents` | Specs, SOPs, architecture docs, agent guides | `.md`, `.txt`, `.yaml`, `.toml` |
| `awa_code` | Source files, functions, classes | `.py`, `.js`, `.ts`, `.html`, `.css` |
| `awa_conversations` | Past agent sessions, decisions | Chat exports, session logs |
| `awa_ontology` | ONT-I1–ONT-I24 invariants, entity types | Files in `_shared/ontology/` |

---

## Neo4j Node Types

```cypher
(:File {path, type, size, last_modified})
(:Chunk {qdrant_id, file_path, chunk_index, token_count})
(:Entity {name, type, ontology_class, confidence})
(:Invariant {code, description, severity, version})
(:AgentStep {step_id, session_id, tool, reasoning, cost_usd})
(:Decision {decision_id, rationale, outcome, timestamp})
```

---

## Frontend (agent-workspace.html) Patterns

### SSE event handling
```javascript
case 'file_accessed':  onFileAccessed(ev.step, ev.file_path, ev.access_type, ev.bytes_read); break;
case 'data_consumed':  onDataConsumed(ev.step, ev.file_path, ev.excerpt, ev.tokens_used, ev.relevance_score); break;
case 'step_reasoning': onStepReasoning(ev.step, ev.rationale, ev.next_action); break;
case 'step_outcome':   onStepOutcome(ev.step, ev.summary, ev.passed_to_next, ev.tokens_in, ev.tokens_out, ev.cost_usd); break;
```

### Cost badge update (must fire on every step_outcome)
```javascript
sessionTokensIn  += ev.tokens_in  || 0;
sessionTokensOut += ev.tokens_out || 0;
sessionCostUsd   += ev.cost_usd   || 0;
updateCostBadge();
```

### Agent mode selector (not guided checkbox — deprecated)
```javascript
const mode = document.getElementById('cfgAgentMode').value;
// Values: 'general' | 'guided' | 'auditor'
// Routes to: /api/agent/stream | /api/guided/stream | /api/auditor/stream
```

---

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...   # Required — Anthropic API key
QDRANT_URL=http://localhost:6333  # Default
NEO4J_URI=bolt://localhost:7687   # Default
NEO4J_USER=neo4j
NEO4J_PASS=yourpassword
DEFAULT_MODEL=claude-sonnet-4-5   # Overridable per request
```

---

## What Copilot Should Always Do in This Repo

1. **Suggest `context_assemble` before file reads** in agent code
2. **Include `qdrant_ingest` after file writes** in agent and tool code
3. **Emit all 4 SSE events** in any new agent step implementation
4. **Respect Clean Architecture layer boundaries** — check import direction
5. **Include `cost_usd` in step_outcome** — never omit it
6. **Use Anthropic SDK** — never suggest OpenAI or other providers
7. **Follow StepProtocolTracker API** — don't emit SSE events manually
8. **Keep Domain classes free of infrastructure imports**

## What Copilot Should Never Do in This Repo

- Suggest reading files without a preceding semantic query
- Add imports from Infrastructure into Domain classes
- Skip `emit_step_outcome` at the end of an agent step
- Generate agent code without the AI-first retrieval pattern
- Suggest adding a non-Anthropic LLM provider
- Create new API endpoints without corresponding SSE event emission
- Omit `qdrant_ingest` after a file write operation

---

*Awareness-AI · GitHub Copilot Instructions · Ontology v2.4 · 2026*
