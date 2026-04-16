# Awareness-AI — GitHub Copilot Agent Suite
# VS Code · GitHub Copilot · Anthropic Claude API
# Ontology v2.4 · Accountable by Design · 2026
# ─────────────────────────────────────────────────────────────────────────────

## What This Is

A complete GitHub Copilot agent configuration for the Awareness-AI platform.
Once installed, every Copilot interaction in this repository is aware of:

- The AI-first retrieval law (semantic before file read)
- The Anthropic Claude model options and their costs
- The SSE event protocol (file_accessed, data_consumed, step_outcome)
- Clean Architecture layer boundaries and violations
- The Qdrant + Neo4j infrastructure
- The real file paths and module structure

---

## Installation

Copy this entire folder structure into your repository root:

```
.github/
├── README.md                                       ← This file
├── copilot-instructions.md                         ← Auto-loaded in every Copilot chat
├── agents/
│   ├── awareness-architectural-auditor.agent.md    ← Architectural audit agent
│   ├── awareness-argus-legal-agent.agent.md        ← Legal intelligence agent
│   ├── awareness-branding-agent.agent.md           ← Brand compliance agent
│   ├── awareness-frontend-localizer.agent.md       ← Frontend i18n agent
│   ├── awareness-IBSCO-PCP-Agent.agent.md          ← IBSCO PCP decision engine agent
│   ├── awareness-pipeline-intelligence-agent.agent.md ← Pipeline intelligence agent
│   └── guides/
│       └── awareness-ai-brand-system.md            ← Brand design system reference
├── docs/
│   └── MODEL_GUIDE.md                              ← Anthropic model reference
├── instructions/
│   └── awareness-coding-standards.instructions.md  ← Auto-loaded coding rules
├── prompts/
│   ├── add-model-selector.prompt.md
│   ├── ai-native-readiness.prompt.md
│   ├── audit-project.prompt.md
│   ├── implement-tool.prompt.md
│   ├── session-init.prompt.md
│   ├── switch-model.prompt.md
│   └── violation-detect.prompt.md
└── skills/
    └── awareness-ai-platform/
        └── SKILL.md                                ← Platform engineering skill

.vscode/
└── settings.json                                   ← Copilot + editor config
```

No additional VS Code extensions required beyond GitHub Copilot.

---

## File Descriptions

### `.github/copilot-instructions.md`
**Auto-loaded. Always in context.**

Everything Copilot needs to know about this repository: file structure,
AI-first law, Anthropic model guide, API endpoints, tool implementations,
SSE event protocol, and what Copilot should and should not generate.

### `.github/prompts/`
**Reusable prompt files.** Reference in Copilot chat with `#file:`.

| File | Use | Invoke with |
|------|-----|-------------|
| `session-init.prompt.md` | Start a new audit session | `#file:.github/prompts/session-init.prompt.md` |
| `audit-project.prompt.md` | Run a complete 18-section audit | `#file:.github/prompts/audit-project.prompt.md` |
| `ai-native-readiness.prompt.md` | Check AI-native implementation | `#file:.github/prompts/ai-native-readiness.prompt.md` |
| `implement-tool.prompt.md` | Build a new agent tool correctly | `#file:.github/prompts/implement-tool.prompt.md` |
| `add-model-selector.prompt.md` | Add model switcher to workspace UI | `#file:.github/prompts/add-model-selector.prompt.md` |
| `switch-model.prompt.md` | Switch active Anthropic model | `#file:.github/prompts/switch-model.prompt.md` |
| `violation-detect.prompt.md` | Find architectural violations | `#file:.github/prompts/violation-detect.prompt.md` |

### `.vscode/settings.json`
Configures Copilot to always include the instructions file and the rules file
in code generation context. Also sets Python formatter, linter, and environment
variables.

### `MODEL_GUIDE.md`
Complete Anthropic model reference: pricing, use-case guidance, extended
thinking, prompt caching, cost calculation formula, frontend and backend
model switcher implementations.

---

## Using Prompts in VS Code

In GitHub Copilot Chat (`Ctrl+Shift+I`), reference a prompt file:

```
@workspace #file:.github/prompts/audit-full.prompt.md
```

Or use the slash command if configured:
```
/audit-full
```

Or copy-paste the prompt content directly for one-off use.

---

## Relationship to the Agent Definition Files

All agent-related files live under `.github/` — the single source of truth:

| Layer | Files | Location |
|-------|-------|----------|
| **Agent Definitions** | `*.agent.md` | `.github/agents/` |
| **Design Guides** | Brand system, style refs | `.github/agents/guides/` |
| **IDE Instructions** | `copilot-instructions.md` | `.github/` (auto-loaded) |
| **Coding Standards** | `*.instructions.md` | `.github/instructions/` (auto-loaded) |
| **Prompt Library** | `*.prompt.md` | `.github/prompts/` |
| **Skills** | `SKILL.md` | `.github/skills/` |
| **Model Guide** | `MODEL_GUIDE.md` | `.github/docs/` |
| **Editor Config** | `settings.json` | `.vscode/` |

Shared ecosystem data (ontology, law corpus, contracts) lives in `_shared/`.
Project-specific code lives in each project folder.

---

## Quick Start

1. Open Copilot Chat in VS Code
2. Run the session initialization prompt:
   ```
   @workspace #file:.github/prompts/session-init.prompt.md
   ```
3. Follow up with the full audit:
   ```
   @workspace #file:.github/prompts/audit-project.prompt.md
   ```
4. Watch the model cost in the cost badge (bottom of workspace UI)

---

*Awareness-AI · GitHub Copilot Agent Suite · Ontology v2.4 · 2026*
