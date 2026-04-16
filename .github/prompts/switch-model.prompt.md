---
name: switch-model
description: "Switch the LLM model for agent operations. Use when asked to change model, select a different Claude model, or optimize for cost/quality."
---

Help the user switch the active LLM model.

## Available Models

| Model | ID | Best For | Cost (Input/Output per 1M tokens) |
|-------|-----|----------|-----------------------------------|
| **Opus 4.6** | `claude-opus-4-6` | Deep reasoning, architecture | $15 / $75 |
| **Sonnet 4.6** | `claude-sonnet-4-6` | Latest balanced | $3 / $15 |
| **Sonnet 4** | `claude-sonnet-4-20250514` | Production default | $3 / $15 |
| **Haiku 4.5** | `claude-haiku-4-5` | Fast, affordable | $0.80 / $4 |

## How to Switch

### Via API
```bash
curl -X POST http://localhost:8078/api/models/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-opus-4-6"}'
```

### Via Config
Edit `awareness/config/config.toml`:
```toml
[llm]
model = "claude-opus-4-6"
```

### Via Workspace UI
Open Agent Workspace → Config tab → Model dropdown → Select model

## Recommendations

- **Architectural audits**: Use Opus for complex dependency analysis
- **Daily agent tasks**: Use Sonnet (default) — best ratio
- **Quick file operations**: Use Haiku — 4x cheaper than Sonnet
- **Extended thinking needed**: Use Opus with thinking enabled
