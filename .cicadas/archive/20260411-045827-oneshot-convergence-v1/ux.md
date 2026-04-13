---
summary: "This design defines the CLI interface and user experience for the oneshot-convergence-v1 initiative. It focuses on providing a complete, intuitive lifecycle for OneShot evaluations, including re-judging functionality, history listing, and milestone management, with a strong emphasis on clear terminal feedback and structured table outputs."
phase: "ux"
when_to_load:
  - "When designing or reviewing journeys, flows, states, copy, and interaction constraints."
  - "When implementation questions depend on experience details rather than product goals alone."
depends_on:
  - "prd.md"
modules:
  - "gavel_ai.cli.commands.oneshot"
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
next_section: "Design Goals & Constraints"
---

# UX Design: oneshot-convergence-v1

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

**Primary goal:** Provide a robust, professional-grade CLI experience that makes managing AI evaluation runs feel predictable and powerful. The user should feel in control of their evaluation history and confident in the reliability of the system.

**Design constraints:**
- **CLI-Only**: All interactions occur in a terminal environment.
- **Stateless Execution**: Commands must rely on the file-system state (`.gavel/evaluations/`).
- **Standard Typer Patterns**: Must follow the existing `gavel <workflow> <command>` structure.

---

## User Journeys & Touchpoints

### Alex (Researcher) — Refining Judges

**Entry point:** Alex has a terminal open after a long evaluation run.
**First touchpoint:** `gavel oneshot judge --help` to discover how to re-run judges.
**Key moment:** Alex sees the "✓ Completed judging" message using the existing outputs, saving them the cost of a full re-run.
**Exit state:** Alex checks the generated `report.html` which now contains the updated scores.
**Pain points to design around:** Unclear feedback on whether the judge actually ran or just read from cache.

---

## Information Architecture

### CLI Structure

```
gavel
└── oneshot
    ├── create (Existing)
    ├── run (Existing - improved)
    ├── judge (NEW - implementation)
    ├── list (NEW)
    └── milestone (NEW)
```

---

## Key User Flows

### Flow 1: Listing Evaluation History

1. **User Action**: `gavel oneshot list --eval media-lens`
2. **System Response**: Renders a table of all runs in `.gavel/evaluations/media-lens/runs/`.
3. **Outcome**: User identifies the correct `run-id` for a specific experiment.

### Flow 2: Marking a Milestone

1. **User Action**: `gavel oneshot milestone --run run_20240101_1200 --comment "Baseline Model"`
2. **System Response**: Updates `run_metadata.json` and prints "✅ Run ... marked as milestone".
3. **Outcome**: The run is now highlighted in future `list` outputs.

---

## UI States

### `oneshot list` Command

| State | Trigger | What the User Sees |
|-------|---------|-------------------|
| **Empty** | No runs found | "No runs found for evaluation '...'. Use 'gavel oneshot run' to start." |
| **Populated** | Runs exist | A Typer-rendered table: `Run ID | Timestamp | Scenarios | Milestone` |
| **Error** | Invalid eval name | "Error: Evaluation '...' not found." |

### `oneshot judge` Command

| State | Trigger | What the User Sees |
|-------|---------|-------------------|
| **Loading** | Reading results.jsonl | "Loading processor outputs from run '...'" |
| **Success** | Judging complete | "✓ Completed judging (X judges applied)" |
| **Error** | No results found | "Error: No results found for run '...'. Did it finish processing?" |

---

## Copy & Tone

**Voice:** Direct, technical, and authoritative. Minimalist feedback but highly informative errors.

**Key principles:**
- **Action-Oriented Symbols**: Use `✓` for success, any errors should clearly state the root cause (e.g., "ConfigError: ...").
- **Consistent Verb Tense**: Use "Completed [task]" or "[Task] finished".

---

## Visual Design Direction

**Style:** Standard terminal output with `rich` tables for data and color-coded status messages.
**Color palette:** 
- **Green**: Success / Milestone markers
- **Yellow**: Warnings / Placeholders
- **Red**: Errors
- **Cyan**: Identifiers (Run ID)
**Spacing & density:** Compact layout to allow many runs to be visible on screen.

---

## UX Consistency Patterns

### Feedback Patterns
- **Success**: `✅ [Action] complete` or `✓ [Task] finished`.
- **Error**: `Error: [Message]` in red.

---

## Responsive & Accessibility

**Accessibility standards:** N/A (CLI-based), but follow standard TTY accessibility (no flashing text, color-usage as secondary indicator).
