---
mode: agent
description: Implement a new agent tool or agent step following the Awareness-AI AI-first protocol. Ensures correct SSE events, token tracking, qdrant_ingest hooks, and Clean Architecture placement.
tools: [context_assemble, qdrant_search, read, write, bash]
---

# Awareness-AI — Implement New Tool or Agent Step

Implement **${input:toolName}** following the full Awareness-AI AI-first protocol.

---

## Step 1 — Retrieve Existing Patterns First

Before writing any code:

```
context_assemble("${input:toolName} similar tools implementation pattern Awareness-AI")
qdrant_search("BaseTool execute async tool implementation", collection="awa_code")
qdrant_search("StepProtocolTracker emit_step_reasoning emit_step_outcome", collection="awa_code")
```

Only read existing tool files if semantic score < 0.72:
```
# If needed: read("app/tool/context_assemble.py") — document escalation reason
```

---

## Step 2 — Determine Architecture Layer

Where does **${input:toolName}** belong?

| If it... | It belongs in... |
|---------|-----------------|
| Accesses Qdrant, Neo4j, files, external APIs | `app/tool/` (Infrastructure) |
| Orchestrates other tools, implements business logic | `app/agent/` (Application) |
| Defines contracts or interfaces | `app/domain/` (Domain) |
| Handles HTTP, SSE, routing | `main.py` or `app/api/` (Presentation) |

**Never place infrastructure imports in Domain classes.**

---

## Step 3 — Tool Implementation Template

```python
# app/tool/${input:toolName:snake_case_name}.py
# Awareness-AI · Ontology v2.4 · AI-First

from app.tool.base import BaseTool, ToolResult
from pydantic import Field
import anthropic
import os

class ${input:toolClassName}(BaseTool):
    """
    ${input:toolDescription}

    AI-First protocol:
    - Calls context_assemble or qdrant_search before any file read
    - Calls qdrant_ingest after any file write
    - Emits step_outcome with cost_usd on completion
    """

    name: str = "${input:toolName}"
    description: str = "${input:toolDescription}"

    # Tool parameters
    query: str = Field(..., description="Natural language description of what is needed")
    # Add more fields as required

    async def execute(self, **kwargs) -> ToolResult:
        # ── 1. SEMANTIC RETRIEVAL FIRST ──────────────────────────────────
        # Always attempt semantic retrieval before any direct file access
        from app.tool.context_assemble import ContextAssembleTool
        ctx_tool = ContextAssembleTool()
        ctx_result = await ctx_tool.execute(query=self.query)

        # Check score — escalate to file read only if below threshold
        SCORE_THRESHOLD = 0.72
        if ctx_result.max_score >= SCORE_THRESHOLD:
            # Use semantic result — no file read needed
            context = ctx_result.context
        else:
            # Document escalation reason, then read
            escalation_reason = f"qdrant score {ctx_result.max_score:.2f} < {SCORE_THRESHOLD}"
            # tracker.emit_step_reasoning(step, f"Escalating: {escalation_reason}")
            # context = open(specific_file).read()
            context = ctx_result.context  # fallback to what we have

        # ── 2. CORE LOGIC ─────────────────────────────────────────────────
        # Implement the tool's primary function here

        # ── 3. INGEST AFTER WRITES ────────────────────────────────────────
        # If this tool writes any file:
        # from app.tool.qdrant_ingest import QdrantIngestTool
        # await QdrantIngestTool().execute(file_path=written_file_path)

        return ToolResult(
            output=f"Result of {self.name}",
            # Include token counts and cost if available
        )
```

---

## Step 4 — Register the Tool

```python
# app/tool/__init__.py — add export
from app.tool.${input:toolName} import ${input:toolClassName}
```

```python
# In the agent that uses this tool — add to tools list:
tools=[
    ContextAssembleTool(),
    QdrantIngestTool(),
    Neo4jQueryTool(),
    ${input:toolClassName}(),  # ← add here
]
```

---

## Step 5 — Add to Workspace Tool Grid

In `static/agent-workspace.html`, add to `#toolGrid`:
```html
<div class="tool-check">
  <input type="checkbox" id="tool_${input:toolName}">
  <label for="tool_${input:toolName}">${input:toolName}</label>
</div>
```

Add icon to `TOOL_ICONS`:
```javascript
${input:toolName}: 'fa-${input:fontAwesomeIcon:wrench}',
```

---

## Step 6 — Post-Write Ingestion

After creating the new tool file:
```
qdrant_ingest("app/tool/${input:toolName}.py", collection="awa_code")
qdrant_ingest("app/tool/__init__.py", collection="awa_code")
```

---

## Step 7 — Write a Unit Test

```python
# tests/tool/test_${input:toolName}.py
import pytest
from app.tool.${input:toolName} import ${input:toolClassName}

@pytest.mark.asyncio
async def test_${input:toolName}_semantic_first():
    """Verify tool uses semantic retrieval before direct file access."""
    tool = ${input:toolClassName}(query="test query")
    result = await tool.execute()
    assert result is not None
    # Add specific assertions
```

```bash
python -m pytest tests/tool/test_${input:toolName}.py -v
```

*Awareness-AI · Ontology v2.4 · Tool Implementation Guide*
