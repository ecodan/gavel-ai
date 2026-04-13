---
summary: "DRY refactor of the oneshot judge pipeline: unify on OutputRecord as the in-pipeline type, loop all variants in ScenarioProcessorStep, group by variant_id in JudgeRunnerStep, reuse pipeline steps in the judge CLI command, and delete the duplicate ReJudge class. Fixes silent multi-variant data loss and eliminates dual code paths."
phase: "clarify"
when_to_load:
  - "When defining or reviewing initiative goals, scope, success criteria, and risks."
  - "When validating that implementation still aligns with the intended problem and outcomes."
depends_on: []
modules:
  - "core/steps/scenario_processor.py"
  - "core/steps/judge_runner.py"
  - "core/steps/report_runner.py"
  - "core/contexts.py"
  - "cli/commands/oneshot.py"
  - "storage/results_exporter.py"
  - "judges/rejudge.py"
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
next_section: null
---

# PRD: judge-dry-fix

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

---

## Executive Summary

The oneshot judge pipeline has accumulated three inter-related problems: `ReJudge` duplicates logic already in `JudgeRunnerStep`, two data formats (`ProcessorResult` and `OutputRecord`) coexist mid-pipeline requiring conversions at every seam, and a hard-coded `variants[0]` in `ScenarioProcessorStep` silently drops results for any eval with more than one variant. This initiative fixes all three together by unifying on `OutputRecord` as the in-pipeline type, looping all variants in the processor step, grouping by `variant_id` in the judge step, and deleting `ReJudge` in favour of reusing the same pipeline steps from the judge CLI command.

### What Makes This Special

- **Silent multi-variant data loss fixed** — Any eval with more than one variant was silently producing wrong results before; this initiative makes multi-variant correct by design.
- **One judge code path** — `ReJudge` is deleted entirely; `gavel oneshot judge` re-runs the same `JudgeRunnerStep` + `ReportRunnerStep` as the main pipeline, eliminating drift.
- **Unified in-pipeline type** — `OutputRecord` replaces `ProcessorResult` as the type that flows through the pipeline, removing mid-flight conversions and the complexity they introduce to every downstream step.

---

## Project Classification

**Technical Type:** Developer Tool / Evaluation Framework  
**Domain:** Infrastructure / ML Evaluation  
**Complexity:** Medium — touches 8+ files, changes a shared pipeline type, deletes a class, and fixes a silent data bug  
**Project Context:** Brownfield — refactoring the existing oneshot judge pipeline in gavel-ai; no new external dependencies, no schema changes to output files

---

## Success Criteria

### User Success

1. **Multi-variant evals produce results for every variant** — Running an eval with `variants: ["model-a", "model-b"]` produces `results_raw.jsonl` and `results_judged.jsonl` entries for both variants, visible in `report.html`.
2. **`gavel oneshot judge` re-runs correctly** — Re-judging an existing run no longer requires duplicated model resolution; the command loads `results_raw.jsonl` and delegates to the standard pipeline steps.
3. **Single-variant evals are unaffected** — All existing single-variant runs continue to produce identical output with no regression.

### Technical Success

1. `ReJudge` class and its test file are deleted; no reference to `ReJudge` remains in production code.
2. `RunContext.processor_results` is typed `Optional[List[OutputRecord]]` throughout the pipeline.
3. `ScenarioProcessorStep` loops over all entries in `eval_config.variants`.
4. `JudgeRunnerStep` groups records by `variant_id` and resolves scenarios by `scenario_id` lookup (no positional `zip`).
5. All unit tests pass; tests updated to use `OutputRecord` mocks where `ProcessorResult` was used before.

### Measurable Outcomes

- 0 regressions in single-variant runs (same JSONL content, same report output).
- Multi-variant runs produce exactly N×M result records (N scenarios × M variants) in `results_raw.jsonl`.
- `results_raw.jsonl` and `results_judged.jsonl` on-disk schemas are unchanged.

---

## User Journeys

### Journey 1: ML Eval Engineer — Running Multi-Variant Benchmarks

Priya is an ML eval engineer at a team building a customer-support LLM. She wants to compare two prompt variants — a concise system prompt and a verbose one — across 100 test scenarios before deciding which to ship. She configures `variants: ["prompt-concise", "prompt-verbose"]` in `eval_config.json` and runs `gavel oneshot run`. Before this initiative, only `prompt-concise` results appeared in the output; she would have shipped the wrong variant without knowing the comparison was silently incomplete. After this fix, both variants run and both appear in `results_judged.jsonl` and `report.html` with their respective `variant_id` labels, giving Priya the head-to-head comparison she needs.

**Requirements Revealed:** Multi-variant loop in processor, `variant_id` grouping in judge step, combined results across variants in report.

---

### Journey 2: Framework Maintainer — Adding a New Judge Without Regression

Marcus maintains gavel-ai and is adding a new judge type. He needs to understand the judge execution path and make sure his changes don't break anything. Before this initiative, he had to update both `JudgeRunnerStep` and `ReJudge` independently, and any divergence between the two was silently untested. After this fix, there is exactly one judge execution path; his new judge integrates once and is exercised by both `gavel oneshot run` and `gavel oneshot judge`. He runs the test suite and sees full coverage without needing to understand a parallel code path.

**Requirements Revealed:** Delete ReJudge, unify judge CLI with pipeline steps, single model resolution path.

---

### Journey Requirements Summary

| User Type | Key Requirements |
|-----------|-----------------|
| **ML Eval Engineer** | Multi-variant loop, `variant_id` grouping, per-variant results in output |
| **Framework Maintainer** | Delete ReJudge, unified judge path, no duplicate model resolution |

---

## Scope

### MVP — v1

**Core Deliverables:**
- `ScenarioProcessorStep`: loop all variants; output `List[OutputRecord]`; convert inline
- `JudgeRunnerStep`: group by `variant_id`; scenario lookup by `scenario_id`
- `ReportRunnerStep`: accept `List[OutputRecord]`; inline `results_judged.jsonl` write
- `judge` CLI command: load `OutputRecord` list, run `JudgeRunnerStep` + `ReportRunnerStep`
- Delete `ReJudge` (`rejudge.py` + `test_rejudge.py`)
- Delete `ResultsExporter`; move `compute_config_hash` to `storage/utils.py`
- Update `RunContext.processor_results` type annotation
- Update unit tests for new types

**Quality Gates:**
- All existing `pytest -m unit` tests pass
- Multi-variant integration smoke test: 2 variants × N scenarios → 2N result rows
- `results_raw.jsonl` and `results_judged.jsonl` schema unchanged (verified by existing schema tests or manual diff)

### Out of Scope (Post-MVP)

- Conversational pipeline — separate code path, not touched
- New judge types or judge configuration changes
- Report HTML format changes
- Autotune workflow
- `--judges` filter option redesign beyond basic removal/pre-filtering

---

## Functional Requirements

### 1. Multi-Variant Scenario Processing

**FR-1.1:** `ScenarioProcessorStep` must loop over all entries in `eval_config.variants` (not only `variants[0]`).
- Each variant produces one `ProcessorResult` per scenario.

**FR-1.2:** Each `ProcessorResult` must be converted to `OutputRecord` immediately inside `ScenarioProcessorStep`, before leaving the step.
- All required fields are available at conversion time: `test_subject`, `variant_id`, `scenario_id`, `timing_ms`, `tokens_prompt`, `tokens_completion`, `error`, `metadata`, `timestamp`.

**FR-1.3:** Each `OutputRecord` must be streamed to `results_raw.jsonl` as it arrives (existing `_spool_result` pattern, writing `OutputRecord` directly).

**FR-1.4:** `context.processor_results` must be set to `List[OutputRecord]` containing all records across all variants.

---

### 2. Variant-Aware Judge Execution

**FR-2.1:** `JudgeRunnerStep` must receive `List[OutputRecord]` from `context.processor_results`.

**FR-2.2:** Records must be grouped by `variant_id` before judge execution.

**FR-2.3:** Scenario lookup must use `scenario_id` (a dict `{s.id: s for s in scenarios}`), replacing positional `zip`.

**FR-2.4:** Model resolution logic remains in `JudgeRunnerStep` and is not duplicated in any CLI command.

---

### 3. Report Generation with OutputRecord Input

**FR-3.1:** `ReportRunnerStep` must accept `List[OutputRecord]` from `context.processor_results`.

**FR-3.2:** `results_judged.jsonl` must be written inline by `ReportRunnerStep`, joining `OutputRecord` with `evaluation_results` on `scenario_id`.

**FR-3.3:** `manifest.json` generation is unchanged.

---

### 4. Unified Judge CLI Command

**FR-4.1:** `gavel oneshot judge` must load `List[OutputRecord]` from `results_raw.jsonl` via `run_ctx.results_raw.read()`.

**FR-4.2:** The loaded records must be assigned to `context.processor_results`.

**FR-4.3:** The command must run `JudgeRunnerStep.execute(context)` then `ReportRunnerStep.execute(context)`.

**FR-4.4:** All model resolution code previously added to the CLI command must be removed (it belongs in `JudgeRunnerStep`).

---

### 5. ReJudge Deletion

**FR-5.1:** `src/gavel_ai/judges/rejudge.py` must be deleted.

**FR-5.2:** `tests/unit/test_rejudge.py` must be deleted.

**FR-5.3:** `ReJudge` must be removed from `src/gavel_ai/judges/__init__.py`.

---

### 6. ResultsExporter Removal

**FR-6.1:** `ResultsExporter` class must be deleted from `src/gavel_ai/storage/results_exporter.py`.

**FR-6.2:** `compute_config_hash` must be moved to `src/gavel_ai/storage/utils.py` (or inlined in `ReportRunnerStep` if it is only used there).

---

### 7. Type Annotation Update

**FR-7.1:** `RunContext.processor_results` type annotation must be changed from `Optional[List[ProcessorResult]]` to `Optional[List[OutputRecord]]`.

**FR-7.2:** All `TYPE_CHECKING` imports in `contexts.py` must be updated accordingly.

---

## Non-Functional Requirements

- **Performance:** No regression in single-variant run latency. Multi-variant runs scale linearly — O(N×M) where N = scenarios and M = variants.
- **Reliability:** `results_raw.jsonl` and `results_judged.jsonl` on-disk formats must remain byte-for-byte schema-compatible with existing files. No silent data loss at any variant count.
- **Security:** No new external inputs or attack surfaces introduced. All file reads are bounded by existing storage layer constraints.
- **Maintainability:** Overall unit test coverage ≥70% (`pytest --cov-fail-under=70 -m unit`). No test file left behind that tests a deleted class. `compute_config_hash` accessible as a standalone utility, not buried in a deleted class.

---

## Open Questions

1. **`context.model_variant` field** — The doc says set it to a comma-joined summary or drop it entirely. Is it used anywhere beyond display/logging? If it is read by any downstream code, we need to decide before implementation. *(Owner: builder; resolve before tech design)*

2. **`--judges` filter option** — The doc says "remove or implement by pre-filtering `eval_config.test_subjects[].judges`". Which is preferred? Removing it is simpler; pre-filtering preserves CLI behaviour. *(Owner: builder; resolve before tasks)*

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Downstream code reads `processor_results` as `ProcessorResult` | Med | High | Grep all usages of `processor_results` before changing type; update every callsite together |
| `compute_config_hash` used in more places than expected | Low | Med | Grep before deleting `ResultsExporter`; extract to `storage/utils.py` regardless |
| Streaming `OutputRecord` misses a field previously set by `ResultsExporter` | Low | Med | Diff `ResultsExporter.export_judged_results` output fields against `OutputRecord` fields before deleting |
| Test suite gaps after deleting `test_rejudge.py` | Low | Low | Verify the deleted test coverage is now exercised by updated `test_steps.py` / `test_report_runner.py` |
| Multi-variant change breaks single-variant users silently | Med | High | Add explicit single-variant regression test; assert result count = N for 1-variant runs |
