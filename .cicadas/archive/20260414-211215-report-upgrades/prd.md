
---
summary: "Upgrade the OneShot HTML evaluation report to match the target design: add execution time and eval name to the header, separate LLM and deterministic judges in the summary, add test-subject context to section headers, and replace the flat expanded-input scenario layout with a collapsible table layout that keeps large-payload reports readable."
phase: "clarify"
when_to_load:
  - "When defining or reviewing initiative goals, users, scope, success criteria, and risks."
  - "When validating that implementation still aligns with the intended problem and outcomes."
depends_on: []
modules:
  - "src/gavel_ai/reporters/templates/oneshot.html"
  - "src/gavel_ai/reporters/oneshot_reporter.py"
  - "src/gavel_ai/core/steps/report_runner.py"
  - "src/gavel_ai/models/runtime.py"
index:
  executive_summary: "## Executive Summary"
  project_classification: "## Project Classification"
  success_criteria: "## Success Criteria"
  user_journeys: "## User Journeys"
  scope: "## Scope"
  functional_requirements: "## Functional Requirements"
  non_functional_requirements: "## Non-Functional Requirements"
  open_questions: "## Open Questions"
  risk_mitigation: "## Risk Mitigation"
next_section: "done"
---

# PRD: Report Upgrades

## Progress

- [x] Executive Summary
- [x] Project Classification
- [x] Success Criteria
- [x] User Journeys
- [x] Scope & Phasing
- [x] Functional Requirements
- [x] Non-Functional Requirements
- [x] Open Questions
- [x] Risk Mitigation

## Executive Summary

The current OneShot evaluation report is missing key run metadata (execution time, eval name label), mixes LLM judge scores and deterministic metric scores in a single undifferentiated summary table, and renders all scenario inputs and responses fully expanded — which produces multi-megabyte HTML files when scenarios contain large payloads such as scraped HTML pages. This initiative upgrades the report template and its data pipeline to match the target design in `.cicadas/drafts/report-upgrades/report.html`, closing all identified gaps without changing the underlying evaluation or judging logic.

### What Makes This Special

- **Readable at scale** — Collapsible inputs and truncated responses keep the report usable regardless of payload size.
- **Semantically clear summaries** — LLM judges and deterministic metrics are reported in separate sub-tables, preventing apples-to-oranges averaging.
- **Rich run context in the header** — Total execution time and labeled eval name are surfaced immediately, reducing the time to interpret a run.

## Project Classification

**Technical Type:** Developer Tool  
**Domain:** ML Evaluation / Observability  
**Complexity:** Medium — touches template HTML/JS, Python reporter logic, and the report data pipeline  
**Project Context:** Brownfield — the reporter, template, and RunData dataclass all exist; this initiative upgrades them without breaking the existing data contract.

---

## Success Criteria

### User Success

A user achieves success when they can:

1. **Read run execution time without opening logs** — Overall Execution Time is visible in the report header immediately after opening the file.
2. **Distinguish LLM judges from deterministic metrics** — The Eval Summary clearly separates the two judge types so scores are never averaged across incompatible scales.
3. **Read a large-input report without scrolling past megabytes of raw content** — Scenario inputs and long responses are collapsed by default and expand on click.

### Technical Success

The system is successful when:

1. **All existing eval runs produce valid reports** — No regression in the report generation pipeline; existing tests pass.
2. **Total execution time is surfaced correctly** — The value in the header matches `run_metadata.json`'s `total_duration_seconds`.
3. **Template renders correctly for evals with no deterministic metrics, no LLM judges, or both** — All conditional blocks degrade gracefully.

### Measurable Outcomes

- Report file size for the `media-lens-headline-extraction` run drops from ~2.2 MB to < 200 KB with default collapse thresholds.
- Zero regressions in `pytest -m unit` and `pytest -m integration`.

---

## User Journeys

### Journey 1: ML Engineer — Reviewing a Completed Eval Run

An ML engineer has just run `gavel oneshot run` on a headline-extraction eval and opens the generated `report.html` in a browser. They want to immediately understand: did this run complete within budget, which variant scored higher, and were there any surprising failures? Today they have to scroll past the header to find timing, and the report's 2 MB size makes it sluggish to load. With this upgrade, execution time appears in the header alongside run ID, variant scores are split into LLM and deterministic sub-tables so comparisons are meaningful, and all the large HTML scenario inputs are collapsed — letting them skim scenario-level results in seconds rather than minutes.

**Requirements Revealed:** Header execution time, labeled eval name, LLM/deterministic separation in summary, collapsible inputs.

---

### Journey 2: ML Engineer — Diagnosing a Low-Scoring Scenario

The engineer notices one scenario has a low score in the summary table and clicks through to the detail section. They want to see the raw input that was sent and the model's response side-by-side with the judge's reasoning. Currently the scenario detail uses a CSS grid that forces them to scroll horizontally on laptops. With the upgrade, variants appear as table columns with truncated responses expandable on click, judge badges trigger inline reasoning, and the scenario header shows which prompt version was used — giving them all context in a compact card.

**Requirements Revealed:** Table layout for scenario detail, truncated/expandable responses, prompt name in scenario header, judge reasoning inline.

---

### Journey Requirements Summary

| User Type | Key Requirements |
|-----------|-----------------|
| **ML Engineer (reviewing run)** | Header execution time, eval name label, LLM/deterministic separation, collapsible inputs |
| **ML Engineer (diagnosing scenario)** | Table layout, expandable responses, prompt name in header, judge reasoning inline, "No scoring data" placeholder |

---

## Scope

### MVP — Minimum Viable Product (v1)

**Core Deliverables:**
- Updated header with labeled eval name field and Overall Execution Time
- Eval Summary split into LLM Judges sub-table (with LLM Avg column) and Deterministic Metrics sub-table
- Performance Summary with test-subject sub-header
- Scenario detail rewritten as table layout with collapsible inputs and truncated+expandable responses
- Reporter data pipeline updated to supply execution time, test-subject info, and scenario count

**Quality Gates:**
- All existing unit and integration tests pass
- Report renders correctly for runs with only LLM judges, only deterministic metrics, and both
- Report renders correctly for runs with no scoring data (empty judge lists)

### Growth Features (Post-MVP)

**v2: Per-variant deterministic breakdowns**
- Show deterministic metrics split by variant (requires model change to `DeterministicRunResult`)

**v3: Interactive filtering**
- Filter scenarios by score range or judge outcome in the browser

### Vision (Future)

- Diff view: compare two run reports side-by-side

---

## Functional Requirements

### 1. Header

**FR-1.1:** The report `<h1>` must display the fixed label "OneShot Evaluation Report" rather than the eval name.
- Acceptance: `<h1>` text is "OneShot Evaluation Report" regardless of eval name.

**FR-1.2:** The header metadata row must include: **Evaluation** (eval name), **Run ID**, **Overall Execution Time** (formatted as `NNs` to 2 decimal places), and **Generated** timestamp.
- Acceptance: All four fields are visible in the header for any run.
- Data source: execution time from `run.telemetry["total_duration_seconds"]`.

---

### 2. Eval Summary

**FR-2.1:** The section heading must be "Eval Summary" (not "Evaluation Summary").

**FR-2.2:** For each test subject, render a sub-heading `<h3>` with the subject name (e.g., `sample_prompt:v1`).

**FR-2.3:** Below the subject sub-heading, render a context line showing **Input Source** (e.g., `file.local (scenarios.json)`) and **Number of Scenarios** (integer count).
- Data source: `run.metadata["input_source"]` and `run.metadata["scenario_count"]`.

**FR-2.4:** If LLM judge scores exist, render an `<h4>LLM Judges</h4>` label followed by the judge scores table.
- The rightmost column must be labeled "LLM Avg" and must average only LLM judge columns (not deterministic metrics).

**FR-2.5:** If deterministic results exist, render an `<h4>Deterministic Metrics</h4>` label followed by a summary table showing metric name and population score per metric.

---

### 3. Performance Summary

**FR-3.1:** For each test subject, render a sub-heading `<h3>` with the subject name above the performance table.

**FR-3.2:** The column "Avg Turn Time" must be renamed to "Avg Response Time".

---

### 4. Scenario Detail

**FR-4.1:** Scenario inputs longer than a configurable threshold (default 200 characters) must be rendered collapsed by default with an "expand" toggle; the full text is revealed on click.

**FR-4.2:** Model responses longer than a configurable threshold (default 500 characters) must be truncated to a preview with an "expand" toggle; the full text is revealed on click.

**FR-4.3:** The scenario detail layout must use an HTML `<table>` with variant names as column headers and a response row and a scoring row, replacing the CSS comparison-grid.

**FR-4.4:** The scenario header `<h3>` must include the test-subject name (prompt version) as a right-aligned secondary label.

**FR-4.5:** When a variant has no judgments, the scoring cell must display "No scoring data" in a muted style.

---

## Non-Functional Requirements

- **Performance:** Report generation time must not increase by more than 100ms for runs up to 100 scenarios; the HTML collapse approach must not require client-side JS frameworks.
- **Reliability:** If `run.telemetry["total_duration_seconds"]` is missing or None, the header must fall back to omitting the execution time field rather than failing.
- **Security:** No new external HTTP requests in the generated HTML; all JS is self-contained in the template.
- **Maintainability:** Collapse thresholds (200 chars input, 500 chars response) must be defined as named constants in the reporter, not hardcoded in the template.

---

## Open Questions

- **Q1 (answered):** Should deterministic metrics appear in the Eval Summary or only in the bottom detail section? → Both: aggregated population score in summary, per-sample breakdown at bottom.
- **Q2:** Should the "Input Source" string be constructed in the reporter or in the template? Prefer reporter (keeps template logic thin).
- **Q3:** Is the collapse threshold (200 / 500 chars) the right default? Can adjust based on review — these are configurable constants.

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Template change breaks existing integration tests that assert on report HTML structure | Med | Med | Update integration tests alongside template changes |
| `total_duration_seconds` absent from older or test RunData objects | Med | Low | Graceful fallback — omit field if None |
| Very large number of variants breaks table column widths | Low | Low | CSS `table-layout: fixed` with percentage widths |
| Collapse JS interacts poorly with browser print | Low | Low | Post-MVP; add `@media print` expansion rule if needed |
