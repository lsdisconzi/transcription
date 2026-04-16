# MODEL GUIDE — Awareness-AI
# Anthropic Claude API · Model Selection, Cost Reference & Switching
# Ontology v2.4 · 2026
# ─────────────────────────────────────────────────────────────────────────────

## Why Anthropic Claude — and Only Claude

Awareness-AI uses the Anthropic Claude API exclusively.

This is not a cost decision or a capability comparison. It is an architectural
principle that aligns with what Awareness-AI is:

**A platform built on accountability, transparency, and auditability.**

| Alignment | How Anthropic Delivers It |
|-----------|--------------------------|
| Constitutional AI | Safety built into the model at training — not bolted on after |
| Transparency | Published model cards, system prompt visibility, usage policies |
| Accountability | API usage is logged, attributable, and auditable per call |
| Structured reasoning | Extended thinking enables the multi-hop architectural reasoning this agent requires |
| Predictable behavior | Consistent responses support reproducible audit trails |
| Ethical alignment | Anthropic's published principles align with Awareness-AI's "Accountable by Design" mission |

Switching to a different provider would break the trust model, not just the code.

---

## Available Models

### claude-opus-4-5 — *Deep Reasoning*

```
Model ID:    claude-opus-4-5
Context:     200K tokens
Input cost:  $15.00 / 1M tokens
Output cost: $75.00 / 1M tokens
Cache read:  $1.50  / 1M tokens
```

**Use for:**
- Complex multi-step architectural audits with many dependencies
- Extended thinking mode — deep dependency graph analysis
- Ambiguous codebases where surface-level analysis is insufficient
- Generating the Transformation Plan (Section 14 of the audit report)
- Any step where reasoning quality outweighs cost concern

**Avoid for:**
- Simple lookups (use Haiku)
- High-volume batch ingestion (use Haiku)
- Routine streaming where Sonnet suffices

**Estimated cost per full audit:**
- Small project (<50 files): ~$0.15–$0.40
- Medium project (50–200 files): ~$0.40–$1.20
- Large project (200+ files): ~$1.20–$4.00

---

### claude-sonnet-4-5 — *Default · Balanced*

```
Model ID:    claude-sonnet-4-5
Context:     200K tokens
Input cost:  $3.00 / 1M tokens
Output cost: $15.00 / 1M tokens
Cache read:  $0.30 / 1M tokens
```

**Use for:**
- Standard architectural audits (the recommended default)
- All 18-section report generation
- Violation detection and dependency analysis
- Code generation and refactoring in Migration Assist / Enforcement Mode
- Sessions where you want quality + reasonable cost

**This is the model used in:** `DEFAULT_MODEL=claude-sonnet-4-5`

**Estimated cost per full audit:**
- Small project: ~$0.03–$0.08
- Medium project: ~$0.08–$0.25
- Large project: ~$0.25–$0.80

---

### claude-haiku-4-5 — *Fast · Cost-Efficient*

```
Model ID:    claude-haiku-4-5
Context:     200K tokens
Input cost:  $0.80 / 1M tokens
Output cost: $4.00 / 1M tokens
Cache read:  $0.08 / 1M tokens
```

**Use for:**
- Qdrant ingestion meta-extraction (extracting chunk titles, doc types)
- Simple query classification (which collection to search?)
- Repeated semantic lookups where cost accumulates
- Batch processing of many small files
- Real-time suggestions in the workspace (fast response needed)

**Avoid for:**
- Complex architectural reasoning
- Dependency graph analysis
- Generating transformation plans

**Estimated cost per full audit:** ~$0.008–$0.06

---

## Prompt Caching

All three models support prompt caching. Enable it for long system prompts
and static context (the audit rules, ontology, architecture guide).

```python
# Enable caching on static content
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": LONG_SYSTEM_CONTEXT,
                "cache_control": {"type": "ephemeral"}  # ← cache this
            },
            {
                "type": "text",
                "text": user_query  # ← not cached (changes per request)
            }
        ]
    }
]
```

Cache read costs:
- Opus:   $1.50/M (vs $15.00/M uncached — **90% savings**)
- Sonnet: $0.30/M (vs $3.00/M uncached — **90% savings**)
- Haiku:  $0.08/M (vs $0.80/M uncached — **90% savings**)

**Cache the audit system prompt.** It doesn't change between steps.

---

## Extended Thinking

Available on Opus and Sonnet. Enables the model to reason step-by-step
before producing an answer. Costs additional tokens for the thinking budget.

```python
response = client.messages.create(
    model="claude-sonnet-4-5",  # or claude-opus-4-5
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000  # how much thinking to allow
    },
    messages=[...]
)

# Access thinking content
for block in response.content:
    if block.type == "thinking":
        thinking_text = block.thinking  # the reasoning chain
    elif block.type == "text":
        answer_text = block.text        # the final answer
```

**Use extended thinking for:**
- Dependency direction analysis (complex import graphs)
- Phase 4 AI-Native Infrastructure planning
- Generating the Violation Matrix (requires careful reasoning per row)
- Any step where the agent needs to reason across many files

**Token budget guidance:**
- Simple step: 2,000–4,000 budget_tokens
- Complex step: 8,000–12,000 budget_tokens
- Maximum allowed: 10,000 (Sonnet), 32,000 (Opus)

---

## Cost Calculation Formula

```python
MODEL_PRICING = {
    "claude-opus-4-5":  {"in": 15.00, "out": 75.00, "cache_read": 1.50},
    "claude-sonnet-4-5": {"in":  3.00, "out": 15.00, "cache_read": 0.30},
    "claude-haiku-4-5":  {"in":  0.80, "out":  4.00, "cache_read": 0.08},
}

def calculate_cost(model: str, tokens_in: int, tokens_out: int,
                   cache_read_tokens: int = 0) -> float:
    p = MODEL_PRICING[model]
    return (
        (tokens_in         / 1_000_000) * p["in"]  +
        (tokens_out        / 1_000_000) * p["out"] +
        (cache_read_tokens / 1_000_000) * p["cache_read"]
    )

# Example: 2,000 tokens in, 1,500 out, Sonnet
cost = calculate_cost("claude-sonnet-4-5", 2000, 1500)
# = (2000/1M * 3.00) + (1500/1M * 15.00)
# = $0.006 + $0.0225 = $0.0285
```

---

## Model Switcher — Backend Implementation

### Environment-based default

```python
# main.py
import os
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-5")
```

### Per-request override

```python
# In the request body, accept an optional model field
class AuditRequest(BaseModel):
    userPrompt: str
    model: str = DEFAULT_MODEL  # override per request
    max_tokens: int = 8192
    use_extended_thinking: bool = False
    thinking_budget: int = 8000
```

### Dynamic model selection based on step complexity

```python
def select_model_for_step(step_type: str, token_estimate: int) -> str:
    """
    Choose the most cost-efficient model for a given step.
    """
    # Simple lookups and indexing → Haiku
    if step_type in ["qdrant_ingest", "simple_query", "classification"]:
        return "claude-haiku-4-5"

    # Standard audit steps → Sonnet
    if step_type in ["violation_detection", "dependency_check", "report_section"]:
        return "claude-sonnet-4-5"

    # Complex reasoning steps → Opus with extended thinking
    if step_type in ["transformation_plan", "architecture_assessment", "causal_analysis"]:
        return "claude-opus-4-5"

    # Default
    return DEFAULT_MODEL
```

---

## Model Switcher — Frontend Implementation

### HTML — Agent workspace config panel

```html
<!-- Inside .config-section "Model" -->
<div class="config-row">
  <div>
    <label class="config-label">Model</label>
    <select id="cfgModel" class="config-select" onchange="updateModelCostPreview()">
      <option value="claude-sonnet-4-5" selected>
        Sonnet 4.5 — Balanced (default)
      </option>
      <option value="claude-opus-4-5">
        Opus 4.5 — Deep Reasoning
      </option>
      <option value="claude-haiku-4-5">
        Haiku 4.5 — Fast &amp; Efficient
      </option>
    </select>
  </div>
  <div>
    <label class="config-label">Est. Cost / Step</label>
    <span id="modelCostPreview"
      style="font-family:var(--mono);font-size:12px;color:var(--gray-hi);
             display:block;padding:8px 10px;border:1px solid var(--border);
             border-radius:6px;background:var(--bg)">
      ~$0.028 / step
    </span>
  </div>
</div>

<!-- Extended thinking toggle -->
<label class="config-toggle">
  <input type="checkbox" id="cfgExtendedThinking">
  <span>Extended thinking <span style="color:var(--gray)">(Sonnet/Opus only)</span></span>
</label>
```

### JavaScript — Cost preview updater

```javascript
const MODEL_COSTS = {
  "claude-opus-4-5":   { in: 15.00,  out: 75.00,  label: "Deep Reasoning" },
  "claude-sonnet-4-5": { in: 3.00,   out: 15.00,  label: "Balanced (default)" },
  "claude-haiku-4-5":  { in: 0.80,   out: 4.00,   label: "Fast & Efficient" },
};

// Assume avg step: 2K tokens in, 1.5K tokens out
const AVG_STEP_IN  = 2000;
const AVG_STEP_OUT = 1500;

function updateModelCostPreview() {
  const model  = document.getElementById('cfgModel').value;
  const costs  = MODEL_COSTS[model];
  const stepCost = (AVG_STEP_IN / 1e6) * costs.in
                 + (AVG_STEP_OUT / 1e6) * costs.out;
  document.getElementById('modelCostPreview').textContent =
    `~$${stepCost.toFixed(4)} / step`;
}

// Run on load
document.addEventListener('DOMContentLoaded', updateModelCostPreview);
```

### Send model with request

```javascript
function getConfig() {
  return {
    model:            document.getElementById('cfgModel')?.value || 'claude-sonnet-4-5',
    extendedThinking: document.getElementById('cfgExtendedThinking')?.checked || false,
    guided:           /* existing guided logic */,
    agentMode:        document.getElementById('cfgAgentMode')?.value || 'general',
  };
}

async function sendMessage(presetText) {
  const config = getConfig();
  const body = {
    userPrompt: message,
    model:      config.model,
    use_extended_thinking: config.extendedThinking,
  };
  // ... rest of sendMessage
}
```

---

## Cost Thresholds & Alerts

| Session Cost | Badge Color | Action |
|-------------|-------------|--------|
| < $0.01 | `var(--gray)` | Normal |
| $0.01 – $0.10 | `var(--gray-hi)` | Note |
| $0.10 – $0.50 | `var(--gray-hi)` | Monitor |
| > $0.50 | `var(--amber)` ⚠️ | Warning emitted |
| > $1.00 | `var(--amber)` 🔴 | Alert in report header |

---

## Quick Decision Guide

```
Need best reasoning quality?      → claude-opus-4-5 + extended thinking
Standard audit session?           → claude-sonnet-4-5 (default)
Running many small tasks?         → claude-haiku-4-5
Batch indexing / qdrant_ingest?   → claude-haiku-4-5
Generating Transformation Plan?   → claude-opus-4-5
Live workspace suggestions?       → claude-haiku-4-5
Everything else?                  → claude-sonnet-4-5
```

---

*Awareness-AI · Model Guide · Anthropic Claude API · Ontology v2.4 · 2026*
