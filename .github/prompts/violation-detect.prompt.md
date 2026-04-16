---
mode: agent
description: Detect specific architectural violations in a project — domain purity, layer boundary crossings, missing repository contracts, controller thickness.
tools: [context_assemble, qdrant_search, neo4j_query, grep, read]
---

# Awareness-AI — Violation Detection

Detect architectural violations in **${input:projectName}** and produce a Violation Matrix.

---

## Check 1 — Domain Purity

```
qdrant_search("domain entities imports infrastructure framework database ORM SQLAlchemy", collection="awa_code")
neo4j_query(template="file_dependents", params={"targetPath": "${input:domainPath:app/domain or SafeGuard.Domain}"})
```

A Domain class has a violation if it imports:
- Any database library (SQLAlchemy, EF Core, Dapper, pymongo, etc.)
- Any HTTP framework (FastAPI, Flask, ASP.NET, Express, etc.)
- Any Infrastructure module

Severity: **Critical** — flag immediately.

## Check 2 — Controller Thinness

```
qdrant_search("controller route handler business logic database query service call", collection="awa_code")
```

A controller has a violation if it:
- Contains business logic beyond input validation
- Makes direct database queries
- Calls multiple services in sequence with conditional logic
- Returns raw domain entities (not DTOs)

Severity: **Critical** if business logic, **High** if raw entities exposed.

## Check 3 — Repository Contracts

```
qdrant_search("IRepository interface abstract domain contract", collection="awa_code")
qdrant_search("Repository implementation concrete infrastructure", collection="awa_code")
```

Violation if:
- No interface defined for a repository in Domain layer
- Service injects concrete repository (not interface)
- Infrastructure repository not implementing a Domain interface

Severity: **High**

## Check 4 — Missing DI Wiring

```
qdrant_search("AddApplication AddInfrastructure ServiceCollection DI registration", collection="awa_code")
```

Violation if:
- Services are not registered via extension methods
- Infrastructure classes are instantiated directly (not injected)
- No DI container configured

Severity: **High**

## Check 5 — Shared Data Duplicates

```
qdrant_search("law corpus transcripts ontology local copy _shared", collection="awa_code")
neo4j_query(template="files_by_entity", params={"entityName": "corpus"})
```

Violation if any project contains its own copy of:
- `_shared/law/` — law corpus JSON
- `_shared/corpus/` — transcripts
- `_shared/ontology/` — ontology spec

Severity: **Medium** — label as SHARED-DATA-DUPLICATE

## Check 6 — AI-Native Gaps (NEW)

```
qdrant_search("qdrant_ingest called after write file modification", collection="awa_code")
qdrant_search("context_assemble before read escalation 0.72", collection="awa_code")
qdrant_search("step_outcome cost_usd tokens_in tokens_out", collection="awa_code")
```

Violation if:
- Files are written without subsequent `qdrant_ingest` call
- Agents read files without preceding semantic query
- `step_outcome` events missing `cost_usd`

Severity: **High** for missing cost_usd, **Medium** for missing qdrant_ingest

---

## Output — Violation Matrix

For each violation found, produce one row:

| Rule Violated | File | Layer | Severity | Fix Recommendation |
|---------------|------|-------|----------|--------------------|
| Domain imports SQLAlchemy | `app/domain/models.py:4` | Domain | Critical | Move ORM to Infrastructure/repositories.py |
| Controller queries DB | `main.py:147` | Presentation | Critical | Extract to ApplicationService |
| No IRepository interface | `app/tool/qdrant_ingest.py` | Infrastructure | High | Add abstract base in app/domain/interfaces/ |
| qdrant_ingest missing after write | `app/agent/auditor_agent.py:89` | Application | High | Add qdrant_ingest call after write on line 91 |

---

## Escalation Note

For each violation that requires reading a specific file to confirm:
```
ESCALATION: qdrant_search returned score [X] for "[query]"
Escalating to direct read of [file_path] to confirm violation.
```

*Awareness-AI · Ontology v2.4 · Violation Detection*
