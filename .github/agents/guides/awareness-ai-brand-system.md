# Awareness-AI Brand & Design System Guide

## For VS Code Agents

This guide defines the complete Awareness-AI visual and tonal identity. Any agent creating or modifying frontend interfaces must follow these specifications.

---

## 1. Identity

| Property | Value |
|----------|-------|
| **Brand Name** | Awareness-AI |
| **Primary Tagline** | Accountable by Design |
| **Secondary Tagline** | Structured Operational Intelligence |
| **Domain** | awareness-ai.tech |
| **Contact** | contato@awareness-ai.com.br |
| **Version** | Ontology v2.4 · 24 Invariants |
| **Copyright** | © 2026 Awareness-AI · Ontology v2.4 · Accountable by Design |

---

## 2. Color Palette

### Core Colors
```css
:root {
  --bg: #191917;           /* Primary background */
  --bg-card: #1e1e1b;      /* Card/elevated surfaces */
  --amber: #c4622d;        /* Primary accent */
  --white: #ede8df;        /* Primary text (warm white) */
  --gray: #6b6560;         /* Secondary text */
  --gray-hi: #9a948c;      /* Tertiary text / interactive labels */
  --border: #2a2926;       /* Default borders */
  --border-hi: #3d3a35;    /* Highlighted borders / hover */
  --max: 1020px;           /* Content max width */
  --r: 8px;                /* Border radius */
}
```

### Usage Rules
- **Never** use pure black (`#000`) or pure white (`#fff`)
- Amber is for accents only — buttons, badges, active states, icons
- All surfaces are warm-toned dark (`#191917` to `#1e1e1b`)
- Text hierarchy: `--white` → `--gray-hi` → `--gray`

---

## 3. Typography

| Element | Font | Weight | Size | Tracking |
|---------|------|--------|------|----------|
| Page titles | Lora | 600 | 46px | -0.01em |
| Section headings | Lora | 600 | 34px | -0.01em |
| Subheadings | Lora | 500 | 20px | normal |
| Body text | Inter | 400 | 16px | normal |
| Labels | Inter | 400 | 11px | 0.16em, uppercase |
| Code/Data | JetBrains Mono | 400 | 13px | normal |
| Badges | JetBrains Mono | 400 | 10px | 0.06em |

Font imports:
```html
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

---

## 4. Navigation Bar (Canonical)

```html
<nav>
  <div class="nav-inner">
    <a href="/" class="nav-logo">
      Awareness-AI
      <span class="nav-logo-sub">Structured Operational Intelligence</span>
    </a>
    <span class="nav-badge">ONT v2.4</span>
  </div>
</nav>
```

CSS: Fixed top, 56px height, `rgba(25,25,23,0.95)` background, `backdrop-filter: blur(20px)`.

---

## 5. Anthropic Partnership Position

The Awareness-AI platform is built exclusively on the Anthropic Claude API.

When referencing this in interfaces or documentation:
- Position as a considered architectural decision, not a limitation
- Emphasize: transparency, security, ethical alignment, reasoning quality
- Do NOT position as "locked in" — position as "purpose-built on"
- Include model information with pricing so users can make informed decisions

---

## 6. Component Library

### Section Badge
```html
<div class="section-badge">Section Title</div>
```

### Stat Card
```html
<div class="stat">
  <span class="stat-num">586+</span>
  <span class="stat-label">Articles Indexed</span>
</div>
```

### Data Table
```html
<table class="data-table">
  <thead><tr><th>Column</th></tr></thead>
  <tbody><tr><td>Value</td></tr></tbody>
</table>
```

### Hero Section
```html
<div class="hero">
  <div class="hero-badge"><span class="dot"></span> ACTIVE</div>
  <h1 class="hero-title">Title <em>with emphasis</em></h1>
  <p class="hero-lead">Description text</p>
</div>
```
