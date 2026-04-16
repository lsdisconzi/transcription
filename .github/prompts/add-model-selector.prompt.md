---
mode: agent
description: Add or update the model selector in the agent workspace — dropdown with cost previews, extended thinking toggle, and per-step cost tracking.
tools: [context_assemble, qdrant_search, read, write]
---

# Awareness-AI — Add Model Selector with Cost Preview

Add a **model selector with real-time cost preview** to the agent workspace.

The selector must show:
- Which Claude model is currently active
- Estimated cost per step for that model
- One-click switching between models
- Extended thinking toggle (Sonnet/Opus only)

---

## Step 1 — Retrieve Current UI Patterns

```
context_assemble("agent-workspace.html config panel cfgModel provider selector")
qdrant_search("config-select config-label config-row config-toggle", collection="awa_code")
```

---

## Step 2 — Backend: Accept Model Per Request

In `main.py`, update the request body schema:

```python
class AgentRequest(BaseModel):
    userPrompt: str
    model: str = os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-5")
    use_extended_thinking: bool = False
    thinking_budget: int = 8000

# In the endpoint handler:
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
create_kwargs = {
    "model": request.model,
    "max_tokens": 8192,
    "system": SYSTEM_PROMPT,
    "messages": messages,
}
if request.use_extended_thinking and request.model in ["claude-sonnet-4-5", "claude-opus-4-5"]:
    create_kwargs["thinking"] = {
        "type": "enabled",
        "budget_tokens": request.thinking_budget
    }
    create_kwargs["max_tokens"] = max(8192, request.thinking_budget + 4096)
```

---

## Step 3 — Frontend: Config Panel HTML

In `static/agent-workspace.html`, replace the existing model input with:

```html
<div class="config-row">
  <div>
    <label class="config-label">Claude Model</label>
    <select id="cfgModel" class="config-select" onchange="updateModelCostPreview()">
      <option value="claude-sonnet-4-5" selected>Sonnet 4.5 · Balanced</option>
      <option value="claude-opus-4-5">Opus 4.5 · Deep Reasoning</option>
      <option value="claude-haiku-4-5">Haiku 4.5 · Fast &amp; Cheap</option>
    </select>
  </div>
  <div>
    <label class="config-label">Est. / Step</label>
    <span id="modelCostPreview"
      style="font-family:var(--mono);font-size:12px;color:var(--gray-hi);
             display:block;padding:8px 10px;border:1px solid var(--border);
             border-radius:6px;background:var(--bg)">
      ~$0.0285
    </span>
  </div>
</div>
<label class="config-toggle">
  <input type="checkbox" id="cfgExtendedThinking">
  <span>Extended thinking
    <span style="color:var(--gray);font-size:11px">(Opus/Sonnet · adds cost)</span>
  </span>
</label>
```

---

## Step 4 — Frontend: JavaScript

Add to the `<script>` block:

```javascript
const MODEL_COSTS = {
  "claude-opus-4-5":   { in: 15.00, out: 75.00 },
  "claude-sonnet-4-5": { in:  3.00, out: 15.00 },
  "claude-haiku-4-5":  { in:  0.80, out:  4.00 },
};
const AVG_IN = 2000, AVG_OUT = 1500;

function updateModelCostPreview() {
  const model = document.getElementById('cfgModel')?.value || 'claude-sonnet-4-5';
  const c = MODEL_COSTS[model] || MODEL_COSTS['claude-sonnet-4-5'];
  const cost = (AVG_IN / 1e6) * c.in + (AVG_OUT / 1e6) * c.out;
  const el = document.getElementById('modelCostPreview');
  if (el) el.textContent = `~$${cost.toFixed(4)}`;
}

// Update getConfig() to include model
function getConfig() {
  return {
    // ... existing fields ...
    model: document.getElementById('cfgModel')?.value || 'claude-sonnet-4-5',
    extendedThinking: document.getElementById('cfgExtendedThinking')?.checked || false,
  };
}

// Update sendMessage body to include model
// In runStream or sendMessage:
const body = {
  userPrompt: message,
  model: config.model,
  use_extended_thinking: config.extendedThinking,
};
```

---

## Step 5 — Ingest Updated Files

```
qdrant_ingest("static/agent-workspace.html", collection="awa_code")
qdrant_ingest("main.py", collection="awa_code")
```

---

## Step 6 — Verify

```bash
# Test model override works
curl -X POST http://localhost:8000/api/auditor/stream \
  -H "Content-Type: application/json" \
  -d '{"userPrompt": "ping", "model": "claude-haiku-4-5"}' \
  --max-time 10
```

Check: the `step_outcome` SSE events should show lower `cost_usd` for Haiku vs Sonnet.

*Awareness-AI · Ontology v2.4 · Model Selector Implementation*
