---
mode: agent
description: Initialize an Awareness-AI audit session. Loads ecosystem context, checks prior findings, and confirms operational mode before beginning any work.
tools: [context_assemble, qdrant_search, neo4j_query]
---

# Awareness-AI — Session Initialization

Initialize a new audit session for **${input:projectName:Project name (e.g. Argus, pinocchio, LegalPipeline, awareness)}**.

## Step 1 — Load Ecosystem Context

Run these in sequence. Do not skip any. Report the score returned by each.

```
context_assemble("Awareness-AI product vision operational intelligence ontology v2.4 ${input:projectName}")
context_assemble("workspace restructuring plan current migration phase ${input:projectName}")
context_assemble("Clean Architecture domain application infrastructure presentation layer rules")
```

## Step 2 — Check Prior Findings

```
qdrant_search("audit session ${input:projectName} past findings violations", collection="awa_conversations", top_k=3)
neo4j_query(template="recently_accessed", params={"since": ${input:since:Timestamp 7 days ago as Unix ms}})
```

## Step 3 — Load Cross-Project Coordination

```
context_assemble("COORDINATION_PROTOCOL CHANGE_LOG PROJECT_STATUS shared contracts")
```

## Step 4 — Report

Report:
- What context was retrieved and at what scores
- What prior audit findings exist for ${input:projectName}
- What has changed since the last session (from CHANGE_LOG)
- What phases are currently open or incomplete

Then ask: **Which operational mode and audit phase should we run today?**

Options:
- `Audit Mode` — read-only, full 18-section report
- `Proposal Mode` — read + generate diffs (no writes)
- `Migration Assist Mode` — read + create new documentation files
- `Enforcement Mode` ⚠️ — requires explicit scope confirmation

---

**AI-First reminder:** Do not read any file directly until context_assemble or qdrant_search returns a score below 0.72. Document any escalation.

*Awareness-AI · Ontology v2.4 · Accountable by Design*
