
---
summary: "CLI-only tool. All user-facing changes are command flags, terminal output messages, and an HTML report section. Consistency with existing gavel CLI patterns is the primary constraint. No visual design work required beyond extending the existing HTML report template."
phase: "ux"
when_to_load:
  - "When designing or reviewing CLI flows, error messages, report copy, and interaction edge cases."
depends_on:
  - "prd.md"
modules:
  - "src/gavel_ai/cli/commands/oneshot.py"
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
next_section: null
---

# UX Design: finish-oneshot

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

**Primary goal:** Users should feel that the tool is correct and complete. Specifically: scaffolding produces configs that run without error, interrupted runs are diagnosable, and report output is authoritative (averages exclude noise, judge types are clearly separated).

**Design constraints:**
- CLI-only. No web UI. No interactive TUI. All feedback is stdout/stderr.
- Existing `gavel oneshot` command structure must not change. Only additions are allowed.
- HTML report template must extend the existing `oneshot.html`; no redesign.
- Error messages must follow the existing format: `Error: <what failed> — <how to fix it>`.
- `--template` is the only new flag on `oneshot create`.

---

## User Journeys & Touchpoints

### Evaluation Engineer — Running a Classification Eval

**Entry point:** Terminal. User wants to set up a new classification benchmark from scratch.  
**First touchpoint:** `gavel oneshot create --eval my_classifier --template classification`  
**Key moment:** The generated `eval_config.json` has `ClassifierMetric` judges pre-wired with `accuracy` and `f1` — no manual config editing required before first run.  
**Exit state:** `gavel oneshot run --eval my_classifier` completes and `report.html` contains a "Deterministic Judges" section showing per-sample prediction vs. actual and a population accuracy value.  
**Pain points to design around:** User might not know what `--template` options exist. Help text must enumerate them clearly.

---

### Prompt Engineer — Externalizing Judge Rubrics

**Entry point:** Existing eval with a verbose `eval_config.json`. User wants to clean it up.  
**First touchpoint:** Opens `eval_config.json`, replaces the `config: {...}` dict with `config_ref: "quality_judge"`, creates `config/judges/quality_judge.toml`.  
**Key moment:** `gavel oneshot run` completes without error — no change in judge behavior.  
**Exit state:** `eval_config.json` is clean; rubric lives in a dedicated, editable TOML file.  
**Pain points to design around:** Unclear error message if TOML file is missing. Error must name the exact file path it tried to load.

---

### CI Operator — Diagnosing an Interrupted Run

**Entry point:** CI logs showing a crashed `gavel oneshot run` job.  
**First touchpoint:** Run directory in artifact storage, specifically `.workflow_status` file.  
**Key moment:** Operator sees the file shows `scenario_processing` completed but `judging` did not — can determine exactly where it failed.  
**Exit state:** Re-run completes (or operator patches the underlying issue). Currently, re-run restarts from scratch; `.workflow_status` is a diagnostic artifact, not yet a resume trigger (resume is post-MVP).  
**Pain points to design around:** Operator must know `.workflow_status` exists. It should be mentioned in the CLI run completion log.

---

## Information Architecture

### CLI Command Tree (additions only)

```
gavel oneshot
├── create [--eval NAME] [--type local|in-situ] [--template default|classification|regression]
│   └── NEW: --template flag routes to typed scaffold generator
├── run [--eval NAME]          # unchanged
├── judge [--eval NAME] [...]  # unchanged
├── report [--eval NAME] [...]  # unchanged
└── list                       # unchanged
```

### Artifact Directory (additions)

```
.gavel/runs/{run_id}/
├── .config/
│   ├── eval_config.json       # existing
│   ├── agents.json            # existing
│   ├── scenarios.json         # existing
│   └── prompts/               # NEW: copied from config/prompts/
│       └── {name}.toml
│   └── snapshot_metadata.json # NEW: what was snapshotted and when
├── .workflow_status           # NEW: JSONL of completed steps
├── results_raw.jsonl          # existing
├── results_judged.jsonl       # existing
├── report.html                # existing (new section added)
└── run.log                    # existing
```

**Navigation model:** No navigation. CLI is imperative; artifacts are files in a directory.

---

## Key User Flows

### Flow 1: Classification Scaffold → Run → Report

1. User: `gavel oneshot create --eval ticket_classifier --template classification`
2. System: creates scaffold with `ClassifierMetric` judges (accuracy, f1), 3 sample scenarios (one wrong expected), `prompts/classifier.toml`, `config/judges/quality_judge.toml` example
3. System prints: `✓ Scaffold created: .gavel/evaluations/ticket_classifier/`
4. System prints: `  Template: classification (ClassifierMetric — accuracy, f1)`
5. User edits `scenarios.json` with real data; replaces `{{ANTHROPIC_API_KEY}}`
6. User: `gavel oneshot run --eval ticket_classifier`
7. System runs: validation → process → judge (deterministic) → report
8. System prints run progress as before (tqdm bars for processing + judging)
9. System prints: `✓ Report: .gavel/runs/run-20260412-143022/report.html`
10. User opens report: sees "Deterministic Judges" section with `prediction | actual` table and population accuracy

**Alternate path A — Wrong expected field path:** Judge skips sample with `skip_reason: "prediction_field not found: response.label"` — displayed inline in the deterministic judge table.

---

### Flow 2: External TOML Judge Config

1. User edits `eval_config.json`: changes `"config": {...}` to `"config_ref": "quality_judge"`
2. User creates `config/judges/quality_judge.toml`
3. User: `gavel oneshot run --eval my_eval`
4. System resolves `config_ref` during judge setup, loads TOML, proceeds normally

**Alternate path A — TOML file missing:**  
System exits with: `Error: Judge config file not found: config/judges/quality_judge.toml — Create the file or remove the config_ref field`

---

### Flow 3: Interrupted Run Diagnostics

1. CI job runs `gavel oneshot run --eval my_eval`, is killed mid-judging
2. Artifact directory exists with `results_raw.jsonl` (complete) and `.workflow_status`
3. Operator opens `.workflow_status`:
   ```jsonl
   {"step": "validation", "completed_at": "2026-04-12T14:30:00Z"}
   {"step": "scenario_processing", "completed_at": "2026-04-12T14:30:45Z"}
   ```
4. Operator sees `judging` is absent — knows processing completed, judging did not
5. CI re-run restarts full run (resume is post-MVP)

---

## UI States

### `gavel oneshot create` Output

| State | Trigger | What User Sees |
|-------|---------|----------------|
| **Success** | Scaffold generated cleanly | `✓ Scaffold created: .gavel/evaluations/{name}/` + template summary line |
| **Error: eval exists** | Eval directory already present | `Error: Evaluation '{name}' already exists — Use a different name or delete the existing directory` |
| **Error: unknown template** | `--template` value not recognized | `Error: Unknown template 'foo' — Available templates: default, classification, regression` |

### Deterministic Judge Report Section

| State | Trigger | What User Sees |
|-------|---------|----------------|
| **Populated** | Deterministic judges ran | "Deterministic Judges" section, table with `Scenario | Prediction | Actual | Score` per sample, population metric value below |
| **All skipped** | All samples skipped (bad field path) | Table shows `—` in score column for every row; population metric shows `N/A (0 samples)` |
| **Partial skip** | Some samples skipped | Skipped rows show `—` in score and skip reason in a tooltip/column; population metric calculated from valid samples only |
| **Absent** | No deterministic judges in config | Section not rendered in report |

### Validator Output

| State | Trigger | What User Sees |
|-------|---------|----------------|
| **Warning** | Unregistered judge type | `Warning: Judge type 'custom.my_judge' is not registered — Run may fail at judging stage` printed before run starts |
| **Error** | Prompt file missing | `Error: Prompt 'my_prompt' not found — Check config/prompts/my_prompt.toml exists` (exits before any LLM calls) |
| **Error** | No scenarios | `Error: Scenario list is empty — Add scenarios to data/scenarios.json` |

### Score Average with Skipped Entries

| State | Trigger | What User Sees |
|-------|---------|----------------|
| **No skips** | All scores valid | Normal average displayed |
| **Some skipped** | Processor errors in run | Average shown with `(2 skipped)` annotation next to the score |

---

## Copy & Tone

**Voice:** Direct and technical. Error messages are actionable, not apologetic. Progress output is minimal — only surface what users need to act on.

**Key principles:**
- Error messages always name what failed AND the exact remediation step.
- Never say "invalid" without naming the value that was invalid.
- Skip reasons in report must be human-readable, not Python exception text.
- Validation warnings appear BEFORE any LLM calls — never buried in logs.

**Critical copy samples:**

| Context | Copy |
|---------|------|
| Classification scaffold created | `✓ Scaffold created: .gavel/evaluations/{name}/` + `  Template: classification (ClassifierMetric — accuracy, f1)` |
| Missing TOML judge config | `Error: Judge config file not found: config/judges/{name}.toml — Create the file or remove the config_ref field` |
| Missing prompt file (validator) | `Error: Prompt '{name}' not found — Check config/prompts/{name}.toml exists` |
| Unregistered judge type (warning) | `Warning: Judge type '{type}' is not registered — Run may fail at judging stage` |
| Report: skip annotation | `(N skipped)` next to average score |
| Report: per-row skip reason | `prediction_field not found: {path}` (inline in deterministic table) |
| Report: deterministic section header | `Deterministic Judges` |
| Snapshot log line | `Config snapshot saved to {run_id}/.config/ (prompts included)` |

---

## Visual Design Direction

**CLI output:** Follows existing tqdm progress bar style. New lines added for scaffold creation use checkmark + indented detail lines (consistent with existing `gavel diagnose` output patterns).

**HTML report:** Extends `oneshot.html` template. The new "Deterministic Judges" section appears below the existing "Judge Summary" table. It uses the same table styling. No new CSS frameworks or colors. The `prediction | actual` column pair is rendered with monospace font to aid alignment.

**`.workflow_status` file:** JSONL format for machine readability. Not intended for direct human consumption — exists for CI operators and future tooling.

---

## UX Consistency Patterns

### CLI Flag Patterns

- New flags (`--template`) follow Typer's `Option` with explicit `help=` text listing all valid values.
- Flag is optional with a default (`default`), consistent with existing `--type` on `oneshot create`.

### Error Message Pattern

All errors follow: `Error: {what} — {fix}`. Warnings follow: `Warning: {what} — {consequence}`. No change from existing convention.

### Report Patterns

- New sections in `oneshot.html` placed after existing sections (additive, never reordering).
- Annotations like `(N skipped)` use muted text color consistent with existing "no data" styling.
- Deterministic judge table header is styled the same as existing judge tables, distinguished only by section heading.

---

## Responsive & Accessibility

**Breakpoints:** N/A — CLI tool. HTML report is desktop-only (no responsive requirement; existing report is not responsive).

**Accessibility standards:** Not applicable for this initiative. HTML report is a developer artifact, not a public-facing product.

**Key requirements:**
- Keyboard navigation: N/A
- Screen reader support: N/A
- Terminal output: no color-only signaling; always pair color with text symbol (e.g., `✓` for success, `Warning:` prefix for warnings)
