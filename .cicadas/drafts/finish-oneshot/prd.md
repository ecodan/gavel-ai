
---
summary: "Bring the OneShot evaluation workflow to full feature completeness: deterministic judges (classifier + regression), external TOML judge configs, typed scaffolding templates, full config snapshots, hardened pre-flight validation, step completion tracking, correct score averaging, a deterministic judge report section, and a working in-situ scaffold."
phase: "clarify"
when_to_load:
  - "When defining or reviewing initiative goals, users, scope, success criteria, and risks."
  - "When validating that implementation still aligns with the intended problem and outcomes."
depends_on: []
modules:
  - "src/gavel_ai/judges"
  - "src/gavel_ai/core/steps"
  - "src/gavel_ai/core/contexts.py"
  - "src/gavel_ai/cli/commands/oneshot.py"
  - "src/gavel_ai/cli/scaffolding.py"
  - "src/gavel_ai/reporters/oneshot_reporter.py"
  - "src/gavel_ai/reporters/templates/oneshot.html"
  - "src/gavel_ai/models"
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

# PRD: finish-oneshot

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

The OneShot evaluation workflow has a functioning core but several capability gaps that prevent it from being a complete, production-ready evaluation tool. This initiative closes those gaps: adding zero-LLM-call deterministic judges for structured output evaluation, external TOML-based judge configuration, typed scaffolding templates, full config snapshots, hardened validator checks, step-completion tracking for resumability, corrected score averaging, a dedicated deterministic judge report section, and a working in-situ eval scaffold. When complete, the OneShot workflow will be a fully reliable, reproducible, and ergonomic evaluation pipeline.

### What Makes This Special

- **Zero-LLM deterministic judges** — Enables exact, reproducible evaluation of structured outputs (classification labels, numeric predictions) without incurring LLM API costs.
- **Full run reproducibility** — Prompt files are included in the config snapshot, making every run artifact self-contained and portable.
- **Step-aware resumability** — A `.workflow_status` file lets interrupted runs pick up where they left off rather than restarting from scratch.

---

## Project Classification

**Technical Type:** Developer Tool / Evaluation Framework  
**Domain:** AI/ML Infrastructure  
**Complexity:** Medium — multiple independent subsystems each requiring targeted changes; no single large architectural shift.  
**Project Context:** Brownfield — all changes extend the existing `gavel-ai` OneShot workflow. No greenfield components.

---

## Success Criteria

### User Success

A user achieves success when they can:

1. **Run a classification or regression eval end-to-end** — Scaffold a new eval with `--template classification` or `--template regression`, run it, and receive a report that includes a deterministic judge section with per-sample prediction/actual columns and a population metric value.
2. **Externalize judge definitions** — Define judge criteria in a `config/judges/*.toml` file and reference it by name in `eval_config.json` without duplicating config inline.
3. **Resume an interrupted run** — Kill and restart a run; the workflow detects which steps completed and skips them rather than re-running from the beginning.

### Technical Success

The system is successful when:

1. **All existing unit and integration tests pass** with the new code in place.
2. **Deterministic judge scores are excluded from the LLM judge rollup average**, and the report renders them in a separate section.
3. **Config snapshots include prompts**, so the full run can be reproduced from the `.config/` artifact directory alone.
4. **Pre-flight validation surfaces all known config errors** before any LLM call is made.

### Measurable Outcomes

- `ClassifierMetric` and `RegressionMetric` produce correct population metrics (verified against scikit-learn directly in unit tests).
- Error outputs (processor failures) do not affect judge score averages.
- `snapshot_run_config()` copies prompt TOML files into the run artifact directory.
- `ValidatorStep` raises `ConfigError` when prompt files referenced in config do not exist on disk.

---

## User Journeys

### Journey 1: The Evaluation Engineer — Adding a Classification Benchmark

An evaluation engineer is adding a new benchmark for a system that classifies support tickets into categories. They want zero-LLM-cost ground-truth scoring so every CI run is fast and deterministic. They run `gavel oneshot create --template classification`, get a working scaffold with a `ClassifierMetric` judge wired to `accuracy` and `f1`, drop in their scenarios, and run it. The HTML report renders a separate "Deterministic Judges" table showing the predicted vs. actual label for each scenario and the population accuracy. They commit the run artifact to git knowing it's fully reproducible: prompts are included in the snapshot.

**Requirements Revealed:** `--template classification` scaffold, `ClassifierMetric` judge, deterministic judge report section, prompt snapshot.

---

### Journey 2: The Prompt Engineer — Externalizing Judge Rubrics

A prompt engineer is running an eval with a complex multi-step rubric that was cluttering their `eval_config.json`. They move the rubric to `config/judges/quality_judge.toml` and update the judge entry to `"config": "quality_judge"`. On the next run, the system resolves the reference and the eval behaves identically. They no longer need to update `eval_config.json` when refining the rubric.

**Requirements Revealed:** External TOML judge config resolution, scaffolded example TOML.

---

### Journey 3: The CI Operator — Diagnosing an Interrupted Run

A CI run is killed mid-way (OOM). The operator re-triggers the job. The new run reads `.workflow_status`, sees that `process` completed but `judge` did not, and skips the processing step entirely — saving API cost and time. The final report is identical to what a full run would have produced.

**Requirements Revealed:** `.workflow_status` step tracking, resume-aware workflow.

---

### Journey Requirements Summary

| User Type | Key Requirements |
|-----------|-----------------|
| **Evaluation Engineer** | Deterministic judges, classification/regression templates, prompt snapshots, deterministic report section |
| **Prompt Engineer** | External TOML judge configs, scaffolded example, clear CLI help text |
| **CI Operator** | Step completion tracking, resume on interruption, correct score averaging |

---

## Scope

### MVP — Minimum Viable Product (v1)

**Core Deliverables:**
- OS-1: Deterministic judges (`ClassifierMetric`, `RegressionMetric`) with batch finalization hook
- OS-2: External TOML judge config file resolution
- OS-3: `--template classification` and `--template regression` scaffolds
- OS-4: Config snapshot includes `config/prompts/` directory
- OS-5: Expanded pre-flight validator (variant resolution, prompt existence, judge type, scenario count)
- OS-6: `.workflow_status` step completion tracking and `mark_step_complete` / `get_completed_steps`
- OS-7: Error/None scores excluded from judge score averages; `skipped_count` shown in report
- OS-8: Deterministic judge section in HTML report (prediction|actual columns, population metric, no LLM rollup)
- OS-9: Working `--type in-situ` scaffold (correct `test_subject_type`, no spurious prompt files)

**Quality Gates:**
- All new code covered by unit tests with `@pytest.mark.unit`
- No regressions in existing `pytest -m unit` or `pytest -m integration` suite
- `scikit-learn` added as a declared dependency in `pyproject.toml`

### Growth Features (Post-MVP)

**v2: Markdown judge configs**
- Support `"markdown_path"` field for rich rubric files with `## Criteria`, `## Evaluation Steps`, `## Threshold`, `## Guidelines` sections.

**v2: Workflow resumability**
- Respect `.workflow_status` at run start to skip already-completed steps.

### Vision (Future)

- Schema documentation (`docs/specs/schema-configs.md`, `docs/specs/schema-outputs.md`) for all config and output file fields.

---

## Functional Requirements

### 1. Deterministic Judges

**FR-1.1:** The system must provide a `DeterministicJudge` base class that extracts values via dotted-path lookup from a `processor_output` JSON dict and a `scenario` dict, with no LLM call.
- Skips with `{"skip_reason": "outputs is not a dict"}` if output is not parseable JSON.
- Skips with `{"skip_reason": "prediction_field not found: <path>"}` if the dotted path does not resolve.

**FR-1.2:** The system must provide a `ClassifierMetric` judge that computes a per-sample binary score (1.0 / 0.0 on case-insensitive string label match) and a population metric via scikit-learn.
- Supported `report_metric` values: `accuracy`, `f1`, `precision`, `recall`, `balanced_accuracy`, `matthews_corrcoef`, `cohen_kappa`, `jaccard`, `zero_one_loss`, `hamming_loss`, `fbeta`.
- Optional fields: `average` (binary/macro/micro/weighted), `positive_class`, `beta` (required for fbeta).

**FR-1.3:** The system must provide a `RegressionMetric` judge that computes a per-sample signed error score and a population metric via scikit-learn.
- Supported `report_metric` values: `mean_absolute_error`, `mean_squared_error`, `root_mean_squared_error`, `median_absolute_error`, `max_error`, `r2_score`, `mean_absolute_percentage_error`, `explained_variance_score`.

**FR-1.4:** `JudgeRegistry` must register `"classifier"` → `ClassifierMetric` and `"regression"` → `RegressionMetric`.

**FR-1.5:** `JudgeExecutor` must expose a batch-finalization hook so deterministic judges can compute their population metric after all per-sample calls complete.

**FR-1.6:** `scikit-learn` must be added to `pyproject.toml` dependencies.

---

### 2. External Judge Config Files

**FR-2.1:** When a judge entry's `config` field is a string (not a dict), the system must resolve it as a TOML file at `config/judges/{value}.toml` relative to the eval directory.
- Fields read: `criteria`, `evaluation_steps`, `threshold`.

**FR-2.2:** `LocalFileSystemEvalContext` must expose a `get_judge_config(name: str) -> dict` method that loads and parses the TOML file.

**FR-2.3:** `JudgeRunnerStep` must call `get_judge_config()` when a string reference is encountered, before passing config to the judge.

**FR-2.4:** The scaffold must write an example `config/judges/quality_judge.toml` when generating templates.

---

### 3. Scaffolding Templates

**FR-3.1:** `gavel oneshot create` must accept a `--template` option with values `default`, `classification`, and `regression`.

**FR-3.2:** The `classification` template must generate: `eval_config.json` with `ClassifierMetric` judges (accuracy + f1), `scenarios.json` with 3 sample scenarios (one deliberately wrong `expected`), and `prompts/classifier.toml`.

**FR-3.3:** The `regression` template must generate: `eval_config.json` with a `RegressionMetric` judge (mean_absolute_error), `scenarios.json` with 3 numeric scenarios (one wrong expected), and `prompts/regressor.toml`.

**FR-3.4:** `create` help text must document the available templates and their purpose.

---

### 4. Config Snapshot: Include Prompts

**FR-4.1:** `snapshot_run_config()` must copy all files from `eval_dir/config/prompts/` into `{run_id}/.config/prompts/`. If the directory does not exist, skip silently.

**FR-4.2:** `snapshot_run_config()` must write a `{run_id}/.config/snapshot_metadata.json` recording which files were snapshotted and the snapshot timestamp.

---

### 5. Expanded Pre-flight Validation

**FR-5.1:** `ValidatorStep` must re-enable and fix variant → model resolution (currently commented out), handling both direct model names and agent references.

**FR-5.2:** `ValidatorStep` must validate that prompt files referenced in `test_subjects[*].prompt_name` exist by calling `eval_ctx.get_prompt(f"{name}:latest")`; surface a `ConfigError` with a clear message if not found.

**FR-5.3:** `ValidatorStep` must validate that each judge type in `test_subjects[*].judges` is registered in `JudgeRegistry`; emit a warning (not an error) for unregistered types.

**FR-5.4:** `ValidatorStep` must re-enable the scenario count check and raise a `ValidationError` if the scenario list is empty.

**FR-5.5:** `ValidatorStep` must emit a structured `ValidationResult` with both `errors` and `warnings` lists in all code paths.

---

### 6. Step Completion Tracking

**FR-6.1:** After a successful `execute()` call in `safe_execute()`, the base step must call `context.mark_step_complete(self.phase)`.

**FR-6.2:** `LocalRunContext` must implement `mark_step_complete(phase: StepPhase)` that appends `{"step": phase.value, "completed_at": ISO8601}` to `{run_id}/.workflow_status` in JSONL format.

**FR-6.3:** `LocalRunContext` must implement `get_completed_steps() -> list[StepPhase]` that reads `.workflow_status` and returns completed phases.

**FR-6.4:** `StepPhase` enum must include `PREPARE = "prepare"`, written by `LocalRunContext.__init__()` after snapshot completes.

---

### 7. Error Output Exclusion from Score Averages

**FR-7.1:** `OneShotReporter._build_context()` must exclude a judgment entry from the running score sum and count when the entry's `score` is `None`, `0` due to an error, or the result has a non-empty `error` field.

**FR-7.2:** The reporter must track `skipped_count` per variant per judge for display in the report.

**FR-7.3:** The HTML report template must display `(N skipped)` next to any judge average that had exclusions.

---

### 8. Deterministic Judge Report Section

**FR-8.1:** `ReportData` model must include a `deterministic_results` field: a list of `DeterministicJudgeResult` objects (each holding `judge_name`, `report_metric`, `population_score`, and `per_sample` list of `{scenario_id, prediction, actual, score, skip_reason}`).

**FR-8.2:** `OneShotReporter._build_context()` must detect deterministic judges (via `JudgeRegistry` type or an `is_deterministic` flag) and route their results into `report_data.deterministic_results` instead of `summary_metrics`.

**FR-8.3:** Deterministic scores must be excluded from the LLM judge average rollup calculation.

**FR-8.4:** The HTML report template must render a "Deterministic Judges" section after the LLM judge summary table, showing `prediction | actual` columns per sample, population metric value, and inline skip reason when present.

---

### 9. In-Situ Scaffold

**FR-9.1:** `generate_eval_config()` must generate `"test_subject_type": "in-situ"` (not `"local"`) when `eval_type == "in-situ"`, and use a remote endpoint config structure for `test_subjects[0]`.

**FR-9.2:** `generate_all_templates()` must skip generating `prompts/assistant.toml` and the prompt key in `agents.json` for in-situ evals.

**FR-9.3:** The `--type` help text in `oneshot create` must reflect the behavioral difference between `local` and `in-situ`.

---

## Non-Functional Requirements

- **Performance:** Deterministic judge per-sample calls must add < 1 ms overhead per sample (no I/O, no network calls). Batch finalization may use scikit-learn in-process.
- **Reliability:** `snapshot_run_config()` must not raise if `config/prompts/` is absent. `get_judge_config()` must raise a clear `ConfigError` if the TOML file is missing (not a generic `FileNotFoundError`). `.workflow_status` writes must be append-only and never block on read.
- **Security:** No user-controlled input in `get_judge_config()` must reach shell or eval paths; only filesystem reads of `.toml` files within the eval directory.
- **Maintainability:** All new judge types must register through `JudgeRegistry` (no hardcoded type checks). New tests must use `@pytest.mark.unit`. The `is_deterministic` flag (or registry type check) must be the single point of truth for routing to the deterministic report section.

---

## Open Questions

- **Batch finalization hook placement**: Should deterministic judges accumulate pairs internally and finalize on a `finalize()` method called by `JudgeExecutor`, or should `JudgeExecutor` collect all per-sample results and call `compute_population_metric(pairs)` at the end? The second approach is cleaner but requires `JudgeExecutor` to know about deterministic judges. — *Resolve at tech design.*
- **`is_deterministic` vs. registry type check**: Is a flag on the judge class preferable to a separate registry lookup for routing deterministic results in the reporter? — *Resolve at tech design.*
- **Workflow resume**: OS-6 defines the tracking file but the workflow is not yet wired to skip already-complete steps. Should the resume logic be in-scope for this initiative or post-MVP? — *Current scope: tracking file only. Resume logic is post-MVP.*

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| scikit-learn version conflicts with existing deps | Low | Medium | Pin a compatible version range in `pyproject.toml`; verify in CI. |
| Deterministic judge population metric runs before all samples are processed | Medium | High | Enforce finalization hook is called by `JudgeExecutor` after the last sample, not per-sample; add a unit test that verifies correct ordering. |
| `.workflow_status` JSONL grows unbounded across many runs | Low | Low | Status file is per-run-id; bounded by number of steps in a single workflow. No action needed. |
| In-situ scaffold change breaks existing `--type local` behavior | Low | High | Add regression tests for both `--type local` and `--type in-situ` scaffolds before merging. |
| HTML template changes break existing report rendering | Low | Medium | Snapshot-test the rendered HTML for a known fixture before and after; diff-check in CI. |
