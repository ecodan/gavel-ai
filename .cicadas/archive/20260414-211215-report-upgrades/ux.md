
---
summary: "Report upgrades UX: data-dense HTML report with collapsible scenario content, clear LLM-vs-deterministic summary split, and rich header metadata. Single-file static output, no build step, minimal JS. Designed for ML engineers reading evals in a browser."
phase: "ux"
when_to_load:
  - "When designing or reviewing journeys, flows, states, copy, and interaction constraints."
  - "When implementation questions depend on experience details rather than product goals alone."
depends_on:
  - "prd.md"
modules:
  - "src/gavel_ai/reporters/templates/oneshot.html"
index:
  design_goals: "## Design Goals & Constraints"
  journeys: "## User Journeys & Touchpoints"
  information_architecture: "## Information Architecture"
  key_flows: "## Key User Flows"
  ui_states: "## UI States"
  copy_tone: "## Copy & Tone"
  visual_design: "## Visual Design Direction"
  consistency: "## UX Consistency Patterns"
  accessibility: "## Responsive & Accessibility"
next_section: "done"
---

# UX Design: Report Upgrades

## Progress

- [x] Design Goals & Constraints
- [x] User Journeys & Touchpoints
- [x] Information Architecture
- [x] Key User Flows
- [x] UI States
- [x] Copy & Tone
- [x] Visual Design Direction
- [x] UX Consistency Patterns
- [x] Responsive & Accessibility

---

## Design Goals & Constraints

**Primary goal:** A user opening a report must reach the three key questions — "Did the run complete?", "Which variant scored best?", "What did the low-scoring scenarios look like?" — in under 30 seconds, regardless of payload size.

**Design constraints:**
- Single static HTML file — no server, no build pipeline, no external JS CDN
- All interactivity via vanilla JS defined inline in the template
- Existing CSS design system (CSS variables, purple gradient header, `--border-light`, etc.) must be preserved; new styles extend, not replace
- Must render acceptably on a 13" laptop at 1440px width
- Report is opened via `file://` in a browser (no HTTP context) — no XHR, no fetch

---

## User Journeys & Touchpoints

### ML Engineer — Run Review

**Entry point:** `file://.../.gavel/evaluations/{name}/runs/{run_id}/report.html` opened from terminal or file explorer.  
**First touchpoint:** Header — gradient banner with eval name, run ID, execution time, generated date.  
**Key moment:** Eval Summary table — variant scores side by side, LLM judges and deterministic metrics in clearly labeled sub-tables.  
**Exit state:** Engineer has identified the best-performing variant and flagged any anomalous scenarios for investigation.  
**Pain points to design around:** Execution time buried (solved by header), mixing LLM/deterministic scores (solved by separation), 2 MB file lag (solved by collapse).

---

### ML Engineer — Scenario Diagnosis

**Entry point:** Low score in Eval Summary triggers scroll to Detailed Analysis.  
**First touchpoint:** Scenario card header with scenario ID and prompt version label.  
**Key moment:** Expanding the input to confirm what was sent, comparing variant responses side by side in the table.  
**Exit state:** Engineer understands what the model received, how it responded, and why the judge scored it low.  
**Pain points to design around:** Long inputs obscure the response (solved by collapse), side-by-side comparison hard on narrow screens (table with fixed columns helps), missing judge reasoning hard to find (click-to-expand badge, same as today).

---

## Information Architecture

### Report Structure

```
Report
├── Header (eval name, run ID, execution time, generated)
├── Eval Summary
│   └── [per test-subject]
│       ├── Subject heading + context (input source, scenario count)
│       ├── LLM Judges table (if any)
│       └── Deterministic Metrics table (if any)
├── Performance Summary
│   └── [per test-subject]
│       ├── Subject heading
│       └── Performance table (variant, avg response time, total time)
├── Detailed Analysis
│   └── [per subject group]
│       └── [per scenario]
│           ├── Scenario header (ID + prompt version float-right)
│           ├── Input row (collapsible)
│           └── Variants table
│               ├── Header row: variant names
│               ├── Response row: truncated output + expand toggle
│               └── Score row: judge badges + "No scoring data" fallback
└── Deterministic Judges (per-sample breakdown, if any)
    └── [per metric]
        ├── Metric heading
        ├── Per-sample table
        └── Population score label
```

### Navigation Model

**Primary nav:** None — single-page linear scroll  
**Secondary nav:** Browser anchor links could be added (Post-MVP)  
**Key entry points:** Top of file (default browser open)

---

## Key User Flows

### Flow 1: Check Run Outcome (Happy Path)

1. User opens report.html
2. Header renders: eval name, run ID, execution time, generated timestamp visible at a glance
3. User reads Eval Summary — sees LLM Judges table with per-variant mean scores and LLM Avg
4. If deterministic metrics exist, reads the Deterministic Metrics table below
5. User reads Performance Summary — sees avg response time per variant
6. User decides whether to drill into scenarios

**Alternate path A:** No judges configured → Eval Summary section is empty/omitted; user proceeds directly to Detailed Analysis.  
**Alternate path B:** Run had failures → Error scenarios appear in Detailed Analysis with error box styling (existing behavior, unchanged).

---

### Flow 2: Diagnose a Specific Scenario

1. User identifies low-scoring variant in Eval Summary
2. User scrolls to Detailed Analysis, finds the scenario card
3. Scenario header shows: `Scenario: {id}` with prompt version right-aligned
4. User sees the collapsed input row; clicks "expand" to reveal full input text
5. User reads truncated response in the variant column; clicks "expand" for full response
6. User clicks a judge badge to reveal reasoning inline
7. User collapses input to restore scanning view

**Alternate path:** Scenario has no judgments → scoring row shows "No scoring data" in muted italic.

---

## UI States

### Header

| State | Trigger | What the User Sees |
|-------|---------|-------------------|
| **Normal** | Report loaded | Gradient banner; all four meta fields visible |
| **Missing execution time** | `total_duration_seconds` absent from run | Execution time field omitted silently |

### Eval Summary — LLM Judges Table

| State | Trigger | What the User Sees |
|-------|---------|-------------------|
| **Populated** | LLM judges ran | Variant rows with mean scores and LLM Avg |
| **Empty** | No LLM judges | Section omitted (no `<h4>LLM Judges</h4>` rendered) |

### Eval Summary — Deterministic Metrics Table

| State | Trigger | What the User Sees |
|-------|---------|-------------------|
| **Populated** | Deterministic metrics ran | Metric name + population score rows |
| **Empty** | No deterministic metrics | Section omitted |

### Scenario Input

| State | Trigger | What the User Sees |
|-------|---------|-------------------|
| **Short input (≤ 200 chars)** | Input below threshold | Full text shown inline, no expand button |
| **Long input (> 200 chars)** | Input above threshold | First line truncated with ellipsis + "expand" button |
| **Expanded** | User clicks "expand" | Full input text shown, button reads "collapse" |

### Scenario Response

| State | Trigger | What the User Sees |
|-------|---------|-------------------|
| **Short response (≤ 500 chars)** | Response below threshold | Full text shown, no expand button |
| **Long response (> 500 chars)** | Response above threshold | Truncated preview (first ~500 chars) + "expand" button |
| **Expanded** | User clicks "expand" | Full response text shown, button reads "collapse" |
| **No response** | Processor error | Error box (existing styling, unchanged) |

### Scoring Row

| State | Trigger | What the User Sees |
|-------|---------|-------------------|
| **Has judgments** | Judges ran for this variant | Judge badges with score; click to expand reasoning |
| **No judgments** | No judges configured or skipped | "No scoring data" in muted italic |

---

## Copy & Tone

**Voice:** Technical and minimal — no marketing language. Precision over friendliness. Labels are clear, not decorative.

**Key principles:**
- Use noun phrases for labels, not sentences ("Overall Execution Time" not "Time taken to complete run")
- Expand/collapse controls use "expand" / "collapse" (lowercase, consistent)
- "No scoring data" (not "N/A", not "—") for empty judge cells — this is specific and searchable
- Section headings match the target design exactly: "Eval Summary", "Performance Summary", "Detailed Analysis", "Deterministic Judges"

**Critical copy samples:**

| Context | Copy |
|---------|------|
| Report h1 | `OneShot Evaluation Report` |
| Eval name header label | `Evaluation:` |
| Execution time label | `Overall Execution Time:` |
| LLM judges sub-heading | `LLM Judges` |
| Deterministic sub-heading | `Deterministic Metrics` |
| LLM average column header | `LLM Avg` |
| No judge data | `No scoring data` |
| Input expand button | `expand` / `collapse` |
| Response expand button | `expand` / `collapse` |
| Input source label | `Input Source:` |
| Scenario count label | `Number of Scenarios:` |

---

## Visual Design Direction

**Style:** Data-dense, compact. Existing gavel-ai report design is the reference — this initiative extends it, does not replace it.  
**Color palette:** Existing CSS variables — `--header-gradient` (purple), `--border-light`, `--text-secondary`. No new color tokens.  
**Typography:** Existing system font stack. `font-size: 13px` body. `font-size: 12px` for table content and badges.  
**Spacing & density:** Compact — preserve the existing 12px/16px padding rhythm.  
**Existing design system:** The existing `oneshot.html` CSS is the design system — extend with new classes, preserve all existing ones.

**New visual elements introduced:**
- `xut-subheader` div (already in draft) — small muted context line below subject heading
- `input-text-wrapper` / `input-text-collapsed` / `input-text-expanded` — already in draft
- `truncated-content` / `truncated-preview` / `truncated-full` — already in draft
- `no-data` div — already in current template (reused for "No scoring data")

---

## UX Consistency Patterns

### Expand/Collapse Controls

All expand/collapse toggles use the same pattern:
- Button text: `"expand"` (default) / `"collapse"` (when open)
- Button class: `expand-btn`
- Button style: small underlined blue link (`color: #3498db`, `text-decoration: underline`, `font-size: 11px`)
- Toggle function: `toggleInput(id)` for inputs, `toggleTruncated(id)` for responses

### Table Layout

- Scenario variant tables use `table-layout: fixed` with equal column widths (`100% / N variants`)
- First column (input row label) is not a full table column — it's a header above the table
- Judge score badges remain `inline-block` within scoring cells

### Judge Reasoning

Clicking a judge badge expands an inline reasoning box below it. This is unchanged from the current design — same `toggleReasoning(id)` function, same `judge-reasoning` class.

---

## Responsive & Accessibility

**Breakpoints:**

| Breakpoint | Width | Layout |
|-----------|-------|--------|
| Mobile | < 768px | Variant table columns stack vertically (existing `@media` rule) |
| Desktop | ≥ 768px | Multi-column table layout |

**Accessibility standards:** No formal WCAG target (developer tool, not public product).

**Key requirements:**
- Expand/collapse buttons must be `<button>` elements (not `<span>` or `<a>`) for keyboard accessibility
- `aria-expanded` attribute on expand buttons would be ideal but is Post-MVP
- Color contrast: existing palette already adequate for dev-tool use
- Touch targets: N/A (desktop-primary tool)
