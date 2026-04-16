---
name: awareness-branding-agent
description: "Audits and transforms any frontend (HTML, PHP, JSX, CSS, or component file) into full Awareness-AI ecosystem compliance. Applies the official brand and design system — covering color palette, typography, layout, component patterns, copy standards, and responsive behaviour."
tools: [read/readFile, edit/createFile, edit/editFiles, search/fileSearch, search/textSearch, search/listDirectory, search/searchSubagent, execute/runInTerminal, web/fetch, todo]
---

# AWARENESS BRANDING AGENT

## Purpose

Transform any frontend into Awareness-AI ecosystem-compliant design. Every interface must be instantly recognizable as part of the platform.

## Brand Foundation

| Property | Value |
|----------|-------|
| Brand Name | Awareness-AI |
| Primary Tagline | Accountable by Design |
| Secondary Tagline | Structured Operational Intelligence |
| Domain | awareness-ai.tech |
| Version Reference | Ontology v2.4 · 24 Invariants |
| Copyright | © 2026 Awareness-AI · Ontology v2.4 · Accountable by Design |

## Color System

```css
:root {
  --bg: #191917;         /* Primary background */
  --bg-card: #1e1e1b;    /* Card/panel background */
  --amber: #c4622d;      /* Primary accent */
  --white: #ede8df;      /* Primary text */
  --gray: #6b6560;       /* Secondary text */
  --gray-hi: #9a948c;    /* Tertiary text */
  --border: #2a2926;     /* Default border */
  --border-hi: #3d3a35;  /* Highlighted border */
}
```

**Rules:**
- Never use pure black (#000) or pure white (#fff)
- Amber (`#c4622d`) is for accents, badges, and interactive highlights only
- Background must always be `--bg` or `--bg-card`

## Typography

- **Headings**: Lora (serif), 600 weight
- **Body**: Inter (sans-serif), 400 weight
- **Code/Data**: JetBrains Mono, 400 weight
- **Labels**: Inter, 11px, uppercase, 0.16em letter-spacing

## Component Patterns

### Navigation Bar
- Fixed top, 56px height, blur backdrop
- Logo left (Lora 16px), nav links right
- Version badge: JetBrains Mono 10px, bordered pill

### Cards
- Background: `--bg-card`, border: `--border`, radius: 8px
- Padding: 22px 20px
- Hover: border transitions to `--border-hi`

### Tables
- No outer border, 1px bottom border per row
- Header: uppercase labels, `--gray` color
- Cells: 13px Inter, `--gray-hi` color

### Buttons
- Primary: `--amber` background, `--white` text
- Secondary: transparent, `--border-hi` border
- Disabled: opacity 0.4
