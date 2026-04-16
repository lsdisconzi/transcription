---
mode: agent
description: Check whether the project fully implements AI-first retrieval, Qdrant semantic layer, Neo4j graph layer, SSE observability, and token cost accounting. Scores each dimension 0–100.
tools: [context_assemble, qdrant_search, neo4j_query, bash, read]
---

# Awareness-AI — AI-Native Readiness Check

Run a focused AI-Native Readiness audit of **${input:projectName}**.

Check whether the project implements all components of the Awareness-AI
observability and semantic retrieval architecture.

---

## Checklist — Run Each Query

### Qdrant Semantic Layer

```
qdrant_search("qdrant_search qdrant_ingest QdrantIngestTool context_assemble ContextAssembleTool", collection="awa_code")
```

Verify:
- [ ] `ContextAssembleTool` exists in `app/tool/context_assemble.py`
- [ ] `QdrantIngestTool` exists in `app/tool/qdrant_ingest.py`
- [ ] Collections exist: `awa_documents`, `awa_code`, `awa_conversations`, `awa_ontology`
- [ ] Post-write hooks call `qdrant_ingest` after file modifications
- [ ] Agent system prompts enforce semantic-first retrieval

```bash
# Verify Qdrant collections live
curl -s http://localhost:6333/collections | python3 -m json.tool
```

### Neo4j Graph Layer

```
qdrant_search("neo4j_query Neo4jQueryTool cypher template graph", collection="awa_code")
```

Verify:
- [ ] `Neo4jQueryTool` exists in `app/tool/neo4j_query.py`
- [ ] Node types registered: `File`, `Chunk`, `Entity`, `Invariant`, `AgentStep`, `Decision`
- [ ] Relationship types: `IMPORTS`, `CONTAINS`, `MENTIONS`, `ACCESSED_IN`, `LED_TO`
- [ ] All 10 Cypher templates implemented
- [ ] `register_step` called after each agent step

```bash
# Verify Neo4j schema live
echo "MATCH (n) RETURN labels(n), count(n) LIMIT 20" | cypher-shell -u neo4j -p $NEO4J_PASS
```

### SSE Observability Layer

```
qdrant_search("step_outcome file_accessed data_consumed step_reasoning StepProtocolTracker", collection="awa_code")
```

Verify:
- [ ] `StepProtocolTracker` exists in `app/agent/step_protocol.py`
- [ ] `emit_step_reasoning` called at start of each step
- [ ] `emit_file_accessed` called when any file is read
- [ ] `emit_data_consumed` called with excerpt, tokens, relevance_score
- [ ] `emit_step_outcome` called with `cost_usd` at end of each step

### Token Cost Accounting

```
qdrant_search("cost_usd tokens_in tokens_out sessionTokensIn costBadge updateCostBadge", collection="awa_code")
```

Verify:
- [ ] `cost_usd` field present in `step_outcome` SSE event
- [ ] `sessionTokensIn`, `sessionTokensOut`, `sessionCostUsd` globals in frontend
- [ ] `updateCostBadge()` called on every `step_outcome` event
- [ ] `#costBadge` element visible in chat header
- [ ] Color-coded: gray (<$0.01), gray-hi ($0.01–$0.50), amber (>$0.50)

### Model Selection UI

```
qdrant_search("model selector dropdown claude-sonnet claude-opus claude-haiku cfgModel", collection="awa_code")
```

Verify:
- [ ] Model selector visible in agent workspace config panel
- [ ] Shows current model and estimated cost per step
- [ ] Supports switching between: `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`
- [ ] Model change propagates to backend and updates cost calculation

### Agent AI-First Compliance

```
qdrant_search("AuditorAgent context_assemble before read escalation score 0.72", collection="awa_code")
```

Verify:
- [ ] `AuditorAgent` system prompt enforces semantic-first retrieval
- [ ] Score threshold 0.72 is defined and enforced
- [ ] Escalations are documented in `step_reasoning` before file reads
- [ ] AI-first pattern documented in `AGENT_GUIDE.md`

---

## Scoring

Score each dimension 0–100:

| Dimension | Score | Notes |
|-----------|-------|-------|
| Qdrant collections created | | |
| qdrant_ingest hooks after writes | | |
| context_assemble as first tool | | |
| Neo4j schema populated | | |
| Neo4j Cypher templates (10/10) | | |
| file_accessed events emitted | | |
| data_consumed events emitted | | |
| step_outcome with cost_usd | | |
| cost badge in UI | | |
| Model selector with cost preview | | |
| Agent prompts enforce AI-first | | |

**Total / 1100 = AI-Native Readiness %**

Produce Section 12 of the standard audit report.

*Awareness-AI · Ontology v2.4 · AI-Native Readiness Check*
