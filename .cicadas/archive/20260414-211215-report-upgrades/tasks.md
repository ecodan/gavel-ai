
---
summary: "Two partitions, 13 tasks total. Partition 1 (data-pipeline): 5 tasks to extend report_runner.py and oneshot_reporter.py with new context fields. Partition 2 (template): 7 implementation tasks rewriting all four HTML sections plus test updates. Initiative PR to master at the end."
phase: "tasks"
when_to_load:
  - "When selecting the next implementation task or reviewing completion state."
  - "When checking partition progress, PR boundaries, or execution sequencing."
depends_on:
  - "prd.md"
  - "ux.md"
  - "tech-design.md"
  - "approach.md"
modules:
  - "src/gavel_ai/core/steps/report_runner.py"
  - "src/gavel_ai/reporters/oneshot_reporter.py"
  - "src/gavel_ai/reporters/templates/oneshot.html"
  - "tests/"
index:
  partition_one: "## Partition: feat/report-upgrades/data-pipeline"
  partition_two: "## Partition: feat/report-upgrades/template"
  initiative_boundary: "## Initiative Boundary"
next_section: "## Partition: feat/report-upgrades/data-pipeline"
---

# Tasks: Report Upgrades

## Partition: feat/report-upgrades/data-pipeline

- [ ] Add `INPUT_COLLAPSE_THRESHOLD = 200` and `RESPONSE_TRUNCATE_THRESHOLD = 500` as module-level constants in `oneshot_reporter.py` <!-- id: 1 -->
- [ ] Extend `ReportRunnerStep.execute()` in `report_runner.py` to add `input_source` (formatted as `"{source} ({name})"` from `eval_config.scenarios`) and `subject_names` (list of `prompt_name` values from `eval_config.test_subjects`, falling back to unique `test_subject` values from `processor_results`) to the `RunData.metadata` dict <!-- id: 2 -->
- [ ] Extend `OneShotReporter._build_context()` to extract `total_execution_time_s` from `run.telemetry.get("total_duration_seconds")` (None if missing), `input_source`, `subject_names`, and `scenario_count` from `run.metadata`, and inject all five values plus the two threshold constants into the returned context dict <!-- id: 3 -->
- [ ] Add unit tests for `_build_context` covering: new context keys present, `total_execution_time_s` is `None` when telemetry missing, `input_source` formatted correctly, `subject_names` fallback to results-derived list <!-- id: 4 -->
- [ ] Run `pytest -m unit` and confirm all tests pass <!-- id: 5 -->

## Partition: feat/report-upgrades/template

- [ ] Copy all new CSS classes from `.cicadas/drafts/report-upgrades/report.html` into `oneshot.html` `<style>` block: `.header-meta`, `.time-value`, `.xut-subheader`, `.input-text-wrapper`, `.input-text-collapsed`, `.input-text-expanded`, `.input-text-wrapper.expanded` rules, `.truncated-content`, `.truncated-preview`, `.truncated-full`, `.truncated-content.expanded` rules, `.model-response`, `.no-data` (keep existing), `.system-prompt` updates <!-- id: 6 -->
- [ ] Add `toggleInput(id)` and `toggleTruncated(id)` JS functions to `oneshot.html` `<script>` block alongside existing `toggleReasoning(id)` <!-- id: 7 -->
- [ ] Replace `<header>` block: fixed `<h1>OneShot Evaluation Report</h1>`, `.header-meta` div with Evaluation, Run ID, conditional Overall Execution Time (`{% if total_execution_time_s is not none %}`), and Generated fields <!-- id: 8 -->
- [ ] Replace `<section id="summary">` block: heading "Eval Summary"; iterate `subject_names` for sub-heading + `.xut-subheader` context line; conditional `<h4>LLM Judges</h4>` + summary table with "LLM Avg" column header; conditional `<h4>Deterministic Metrics</h4>` + population-score table; `{% else %}` fallback for empty subject_names renders flat tables as before <!-- id: 9 -->
- [ ] Update `<section id="performance">` block: add `<h3>{{ subject }}</h3>` sub-heading per subject (iterate `subject_names` with same fallback); rename column header "Avg Turn Time" → "Avg Response Time" <!-- id: 10 -->
- [ ] Replace scenario detail section with table layout: `input-section` div per scenario; collapsible input (`toggleInput`, collapse when `system_input|length > input_collapse_threshold`); `<table>` with variant `<th>` headers; response row with `truncated-content` when `output|length > response_truncate_threshold`; score row with judge badges or `.no-data` "No scoring data"; test-subject name float-right in scenario `<h3>` header <!-- id: 11 -->
- [ ] Update integration test assertions in `test_oneshot_pipeline_e2e.py` (and any other tests asserting on report HTML) to match new template structure; run `pytest -m unit && pytest -m integration` and confirm all pass <!-- id: 12 -->

## Initiative Boundary

- [ ] Open PR: initiative/report-upgrades -> master and await merge approval before continuing <!-- id: 100 -->
