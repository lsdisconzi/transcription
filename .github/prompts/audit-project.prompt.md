---
mode: agent
description: Run a complete 18-section architectural audit in Audit Mode (read-only). Uses AI-first retrieval throughout — semantic before file access.
tools: [context_assemble, qdrant_search, neo4j_query, read, grep, glob, bash, run]
---

# Awareness-AI — Full Architectural Audit

Run a complete architectural audit of **${input:projectName}** in **Audit Mode** (read-only, no modifications).

## Operating constraints for this audit

- Every context retrieval must use `context_assemble` or `qdrant_search` first
- Only escalate to direct file read if relevance score < 0.72
- Document every file escalation in step_reasoning before executing the read
- Token budget per step: 4,096 tokens
- Emit step_outcome before advancing to the next step
- The cost badge must update on every step_outcome

---

## Execution Sequence

### Step 1 — Context & Stack Detection

```
context_assemble("${input:projectName} technology stack manifest files architecture")
```

If score < 0.72, use glob to find: `*.csproj`, `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`

### Step 2 — Dependency Graph

```
neo4j_query(template="file_dependencies", params={"targetPath": "${input:entryPoint:Entry point file path}"})
neo4j_query(template="recently_accessed", params={"since": ${input:since7d:7-day timestamp in Unix ms}})
```

### Step 3 — Architecture Assessment

```
context_assemble("Clean Architecture violations domain purity ${input:projectName}")
context_assemble("DI wiring AddApplication AddInfrastructure service registration ${input:projectName}")
context_assemble("repository interface contracts domain infrastructure ${input:projectName}")
```

### Step 4 — AI-Native Readiness

```
qdrant_search("qdrant_search context_assemble vector store semantic", collection="awa_code")
qdrant_search("neo4j_query graph database cypher", collection="awa_code")
qdrant_search("step_outcome file_accessed data_consumed tokens cost_usd", collection="awa_code")
qdrant_search("SSE streaming events observability", collection="awa_code")
```

### Step 5 — Historical Context

```
qdrant_search("${input:projectName} audit findings violations past sessions", collection="awa_conversations", top_k=5)
```

---

## Output — 18-Section Report

Produce all 18 sections in order. If a section has no findings, state "None identified" with reason.

1. **Executive Structural Summary**
2. **Stack Detection Result** — confirmed technology stack, version, framework
3. **AI-First Retrieval Log** — every semantic query run, score returned, escalations
4. **Repository Map** — directory structure from semantic + graph, not blind tree
5. **Current Architecture Assessment** — pattern identified, deviation from Clean Architecture
6. **Architectural Strengths** — what is well-structured
7. **Architectural Weaknesses** — what needs improvement
8. **Violation Matrix** — tabular, all violations with file path, layer, severity, fix

   | Rule Violated | File | Layer | Severity | Fix Recommendation |
   |---------------|------|-------|----------|--------------------|

9. **Structural Risk Assessment** — Critical → Low groupings
10. **Dependency Direction Report** — from neo4j_query(file_dependencies), all violations
11. **AI-Native Readiness Score** — 10 dimensions, each scored 0–100
12. **Observability Completeness Score** — SSE events, cost badge, token budget enforcement
13. **Dependency Overview** — external packages + internal module graph
14. **Transformation Plan** — phased, referencing real files in this codebase
15. **Suggested Directory Restructure** — before/after tree diagram
16. **Technology-Specific Migration Guide** — stack-appropriate steps
17. **Suggested Documentation Additions** — which files are missing
18. **Session Token & Cost Summary** — total tokens, total cost, cost per step

---

## Reference Architecture

Compare against SafeGuard (⭐⭐⭐⭐⭐ benchmark):
```
qdrant_search("SafeGuard Clean Architecture DI AddApplication repository interface", collection="awa_documents")
```

*Awareness-AI · Ontology v2.4 · Audit Mode · Accountable by Design*
