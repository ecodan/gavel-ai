---
summary: "Uplevel gavel-ai's oneshot and judge capabilities. Adds deterministic judges (ClassifierMetric/RegressionMetric), additional DeepEval judge types, external TOML judge configs, prompt snapshot, schema docs, HTML det. judge section, classification/regression scaffold templates, validator hardening, step completion tracking, error score exclusion, and judge criteria templating."
phase: "clarify"
when_to_load:
  - "When defining or reviewing initiative goals, scope, success criteria, and risks."
  - "When validating implementation alignment with parity requirements."
depends_on: []
modules:
  - "src/gavel_ai/judges/"
  - "src/gavel_ai/cli/"
  - "src/gavel_ai/core/"
  - "src/gavel_ai/reporters/"
  - "src/gavel_ai/models/"
  - "docs/specs/"
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
next_section: "Executive Summary"
---

# PRD: gavel-uplevel

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

Gavel-AI is a capable eval framework. This initiative uplevels its oneshot and judge capabilities to better serve the full range of users who run structured evaluations: adding zero-LLM-call deterministic judges for classification and regression tasks, expanding the set of available DeepEval judge types, enabling judge definitions to live in readable external TOML files, and hardening the core pipeline with reproducible snapshots, step tracking, and accurate score reporting. Schema documentation makes the framework more accessible to new contributors and users alike.

### What Makes This Special

- **Zero-LLM Deterministic Judges** — ClassifierMetric and RegressionMetric enable scikit-learn-backed evaluation of structured outputs without any LLM call, enabling fast, cheap regression detection for classification and regression tasks.
- **Full Oneshot Quality Suite** — Validator hardening, step completion tracking, error-exclusion from averages, criteria templating, and prompt snapshotting close correctness and reproducibility gaps in the core pipeline.
- **External Judge Config Files** — Judge criteria and evaluation steps can live in versioned TOML files alongside the codebase, keeping `eval_config.json` clean and rubrics readable.

## Project Classification

**Technical Type:** Developer Tool / Evaluation Framework  
**Domain:** AI/ML Infrastructure  
**Complexity:** High — 11 distinct capability areas across judges, CLI, core pipeline, reporters, and docs  
**Project Context:** Brownfield — extending a shipped, working framework

---

## Success Criteria

### User Success

A user achieves success when they can:

1. **Run deterministic classification/regression evals** — `gavel oneshot create --template classification` scaffolds a working eval; `gavel oneshot run` produces a report with a `ClassifierMetric` section showing per-sample prediction vs. actual and population accuracy.
2. **Load judge definitions from TOML files** — A judge entry with `"config": "quality_judge"` resolves to `config/judges/quality_judge.toml` without inline JSON in `eval_config.json`.
3. **Resume an interrupted run** — A run interrupted after processing but before judging can be detected via `.workflow_status`.
4. **Reproduce any run from its artifact directory** — The `.config/` snapshot includes prompt TOML files so the run is fully self-contained.

### Technical Success

The system is successful when:

1. **All 11 FR areas are implemented** and covered by unit tests.
2. **No regressions** in existing oneshot, conversational, or autotune workflows.
3. **`scikit-learn` integration** for deterministic judges is tested with real metric computations (not mocked).

### Measurable Outcomes

- All 11 FR areas have associated unit tests.
- `gavel oneshot create --template classification` and `--template regression` produce runnable evals.
- A run artifact directory is fully reproducible: contains all config, scenarios, and prompts needed to re-run.

---

## User Journeys

### Journey 1: ML Engineer running classification evals

An ML engineer has built a ticket-classifier LLM. They want to benchmark label accuracy across prompt variants without burning LLM judge quota on every run. They scaffold a classification eval (`gavel oneshot create --template classification`), drop in 50 labeled scenarios, and run. The report shows per-sample prediction vs. actual and F1 score. They iterate on the prompt and compare scores across runs.

**Requirements Revealed:** Deterministic judges (ClassifierMetric), classification scaffold template, HTML report deterministic section, batch-finalization hook.

---

### Journey 2: Prompt engineer iterating on a GEval judge

A prompt engineer wants to write a GEval judge whose criteria references a per-scenario ground-truth field (`{{expected_category}}`). They also want the judge criteria in a TOML file for readability. They create `config/judges/quality_judge.toml`, reference it from `eval_config.json` via `"config": "quality_judge"`, and use `{{expected_category}}` in the criteria string. Gavel resolves both at evaluation time.

**Requirements Revealed:** External TOML judge config files, criteria templating against scenario columns.

---

### Journey Requirements Summary

| User Type | Key Requirements |
|-----------|-----------------|
| **ML Engineer** | ClassifierMetric, RegressionMetric, classification/regression templates, HTML det. judge section |
| **Prompt Engineer** | External TOML judge configs, criteria templating, expanded DeepEval judge types |
| **Any User** | Schema docs, config snapshot with prompts, validator hardening, step completion tracking |

---

## Scope

### MVP — This Initiative (gavel-uplevel)

**Core Deliverables (11 items — oneshot and judge quality focus):**

1. **Deterministic Judges** — `ClassifierMetric` and `RegressionMetric` with scikit-learn, batch finalization, `JudgeRegistry` registration.
2. **Missing DeepEval Judge Types** — `ToxicityMetric`, `ConversationCompletenessMetric`, `ConversationalGEval`, `TurnRelevancyMetric` added to `JUDGE_TYPE_MAP`.
3. **External Judge Config Files** — TOML (and Markdown) file resolution from a `"config"` field; scaffold generates example TOML.
4. **Config Snapshot: Prompts** — Copy `config/prompts/` into `.config/prompts/` during `snapshot_run_config()`; write `snapshot_metadata.json`.
5. **Schema Documentation** — `docs/specs/schema-configs.md` and `docs/specs/schema-outputs.md`.
6. **HTML Report: Deterministic Judge Section** — Separate rendering path, `prediction | actual` columns, excluded from LLM rollup average.
7. **Oneshot Templates** — `gavel oneshot create --template classification/regression`.
8. **Validator Hardening** — Re-enable variant resolution, prompt existence check, judge type check, scenario count check; emit structured `ValidationResult`.
9. **Step Completion Tracking** — `.workflow_status` JSONL written after each step; `mark_step_complete` / `get_completed_steps` on `LocalRunContext`.
10. **Error Output Exclusion** — Skip `None`/error-flagged scores from averages; show `(N skipped)` in report.
11. **Judge Criteria Templating** — `{{key}}` substitution in `criteria` and `evaluation_steps` from scenario context.

**Quality Gates:**
- All new judge types covered by unit tests.
- No regressions in existing `pytest -m unit` and `pytest -m integration` suites.
- `gavel oneshot create --template classification` produces a runnable eval end-to-end.

### Deferred (Future Initiatives)

- **Closed-Box CLI** (`gavel closed-box create/run/analyze/report`) — deferred.
- **Autotune Promotion** (`autotune create`, per-iteration artifacts, smart stopping) — deferred.
- **Named Personality Profiles** (`PersonalityType` enum, `personality_distribution`) — deferred.
- **Granular Conv CLI Steps** (`conv generate/evaluate/report`, `.workflow_status` for conv) — deferred.
- **Migration Command** (`gavel migrate [--dry-run]`) — deferred.
- **In-Situ Scaffold Fix** (`--type in-situ` generating correct remote endpoint config) — deferred.

### Out of Scope

- **Score scale changes** — Gavel uses 1–10 integers (intentional design choice for human readability; no change).
- **Provider-specific auth mechanisms** — Gavel is provider-agnostic; no vendor-specific authentication integrations.

---

## Functional Requirements

### 1. Deterministic Judges

**FR-1.1:** System MUST provide a `DeterministicJudge` base class in `judges/deterministic_judge.py` that extracts values via dotted-path from processor output (parsed as JSON dict) and scenario dict without any LLM call.

**FR-1.2:** `ClassifierMetric` MUST produce per-sample score (1.0 if labels match case-insensitively, 0.0 otherwise) and compute population metric via scikit-learn. Supported metrics: accuracy, f1, precision, recall, balanced_accuracy, matthews_corrcoef, cohen_kappa, jaccard, zero_one_loss, hamming_loss, fbeta.

**FR-1.3:** `RegressionMetric` MUST produce per-sample signed error (`float(prediction) - float(actual)`) and compute population metric via scikit-learn. Supported metrics: mean_absolute_error, mean_squared_error, root_mean_squared_error, median_absolute_error, max_error, r2_score, mean_absolute_percentage_error, explained_variance_score.

**FR-1.4:** Both judges MUST skip with `{"skip_reason": "outputs is not a dict"}` if processor output is not parseable JSON, and `{"skip_reason": "prediction_field not found: <path>"}` if dotted path doesn't resolve.

**FR-1.5:** `judge_executor.py` MUST provide a batch-finalization hook so deterministic judges can compute population metrics after all per-sample calls complete.

**FR-1.6:** Both judge types MUST be registered in `JudgeRegistry` as `"classifier"` and `"regression"`.

**FR-1.7:** `scikit-learn` MUST be added to `pyproject.toml` dependencies.

---

### 2. Missing DeepEval Judge Types

**FR-2.1:** `DeepEvalJudge.JUDGE_TYPE_MAP` MUST include: `"deepeval.toxicity"` → `ToxicityMetric`, `"deepeval.conversation_completeness"` → `ConversationCompletenessMetric`, `"deepeval.conversational_geval"` → `ConversationalGEval`, `"deepeval.turn_relevancy"` → `TurnRelevancyMetric`.

**FR-2.2:** Default conversational eval scaffold MUST include `conversation_completeness` + `conversational_geval` judges.

**FR-2.3:** CLI help text MUST document recommended thresholds: Toxicity/Hallucination: 0.85–0.95; AnswerRelevancy/Faithfulness: 0.65–0.80; ConversationCompleteness: 0.70–0.85.

---

### 3. External Judge Config Files

**FR-3.1:** When a judge entry's `config` field is a string (not a dict), the system MUST resolve it as `config/judges/{name}.toml` via `eval_ctx.get_judge_config(name)`.

**FR-3.2:** `LocalFileSystemEvalContext` MUST expose `get_judge_config(name: str) -> dict` that parses the TOML file and returns its fields.

**FR-3.3:** `"markdown_path"` field on a judge entry MUST load from a Markdown file and parse `## Criteria`, `## Evaluation Steps`, `## Threshold`, `## Guidelines` sections.

**FR-3.4:** Scaffold (`generate_all_templates()`) MUST create `config/judges/quality_judge.toml` as an example file.

---

### 4. Config Snapshot: Include Prompts

**FR-4.1:** `snapshot_run_config()` MUST copy all files from `config/prompts/` into `{run_id}/.config/prompts/` after snapshotting the three existing config files. MUST skip silently if the directory doesn't exist.

**FR-4.2:** A `snapshot_metadata.json` MUST be written to `{run_id}/.config/` recording what was captured and the snapshot timestamp.

---

### 5. Schema Documentation

**FR-5.1:** `docs/specs/schema-configs.md` MUST document all fields in `eval_config.json`, `agents.json`, `scenarios.json`, and judge config fields with types and defaults.

**FR-5.2:** `docs/specs/schema-outputs.md` MUST document `results_raw.jsonl`, `results_judged.jsonl`, run metadata, telemetry, and `.config/` snapshot structure.

**FR-5.3:** `CLAUDE.md` MUST reference both schema docs as authoritative sources.

---

### 6. HTML Report: Deterministic Judge Section

**FR-6.1:** `oneshot_reporter.py` MUST detect deterministic vs. LLM judges and route them to separate `ReportData` sections.

**FR-6.2:** Deterministic results MUST be excluded from the LLM average rollup calculation.

**FR-6.3:** Jinja2 template MUST render a "Deterministic Judges" section with `prediction | actual` columns per sample and the population metric value.

**FR-6.4:** Skip reason MUST be shown inline when a judgment is skipped.

---

### 7. Oneshot Templates

**FR-7.1:** `gavel oneshot create` MUST accept a `--template` option with values `default`, `classification`, `regression`.

**FR-7.2:** Classification template MUST generate: `eval_config.json` with `ClassifierMetric` judges (accuracy + f1), `scenarios.json` with 3 samples including one wrong expected, `prompts/classifier.toml` returning structured JSON `{"response": "<label>"}`.

**FR-7.3:** Regression template MUST generate: `eval_config.json` with `RegressionMetric` judge (mean_absolute_error), `scenarios.json` with 3 numeric scenarios, `prompts/regressor.toml` returning `{"response": <number>}`.

---

### 8. Validator Hardening

**FR-8.1:** Variant → model lookup MUST be re-enabled and correctly handle both direct model names and agent references.

**FR-8.2:** Validator MUST check that prompt files referenced in `test_subjects[*].prompt_name` exist, raising `ConfigError` if not found.

**FR-8.3:** Validator MUST warn (not fail) if a judge type is unregistered.

**FR-8.4:** Scenario count check MUST be re-enabled with a `ValidationError` if scenarios list is empty.

**FR-8.5:** `ValidatorStep` MUST emit a structured `ValidationResult` with both `errors` and `warnings` lists in all code paths.

---

### 9. Step Completion Tracking

**FR-9.1:** `base.py` `safe_execute()` MUST call `context.mark_step_complete(self.phase)` after a successful `execute()`.

**FR-9.2:** `LocalRunContext` MUST expose `mark_step_complete(phase: StepPhase)` (appends JSONL entry to `.workflow_status`) and `get_completed_steps() -> list[StepPhase]` (reads the file).

**FR-9.3:** `StepPhase.PREPARE = "prepare"` MUST be added; `LocalRunContext.__init__()` MUST write it after snapshot completes.

---

### 10. Error Output Exclusion from Score Averages

**FR-10.1:** `oneshot_reporter.py` MUST skip a judgment entry from running sum and count when `score` is `None`, `0` due to an error, or the result has a non-empty `error` field.

**FR-10.2:** `skipped_count` per variant per judge MUST be added to the context dict.

**FR-10.3:** `oneshot.html` MUST display `(N skipped)` next to any judge average that had exclusions.

---

### 11. Judge Criteria Templating

**FR-11.1:** A `_render_template(template: str, context: dict) -> str` utility MUST perform `{{key}}` substitution using scenario context (no third-party templating library).

**FR-11.2:** Missing keys MUST leave `{{key}}` in place and log a debug message (no crash).

**FR-11.3:** Rendering MUST be applied to `criteria` and `evaluation_steps` in both inline judge configs and externally loaded TOML judge configs.

**FR-11.4:** Render context MUST be built from `scenario.input` (if dict, unpack keys; if string, add as `input`) plus `scenario.metadata` keys.

---

## Non-Functional Requirements

- **Performance:** Deterministic judges must add < 10ms overhead per sample (no LLM calls). Batch-finalization hook must not block the main execution path.
- **Reliability:** All new steps that write to the filesystem must be idempotent (safe to retry). `.workflow_status` must not corrupt on partial writes.
- **Security:** External TOML file loading must be path-restricted to the eval directory; no arbitrary file inclusion.
- **Maintainability:** All new judge types must follow the existing `Judge` base class interface. All new CLI commands must follow the existing Typer app pattern. Test coverage for all 11 FR areas.

---

## Open Questions

- **Batch-finalization hook placement** — Should `judge_executor.py` call the finalization hook unconditionally on all judges (no-op for LLM judges), or only on judges that declare themselves deterministic? (Assumption: opt-in via a `supports_batch_finalization` flag on the base class; revisit in tech design.)
- **TOML Markdown judge parsing** — For `"markdown_path"` judge configs, should missing optional sections (`## Guidelines`) silently default to empty, or warn? (Assumption: silent default.)

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| scikit-learn version conflicts with existing deps | Low | Medium | Pin a compatible version range; test in CI |
| Batch-finalization hook changes judge_executor contract | Medium | Medium | Add hook as optional extension point; existing judges unaffected |
| TOML file path traversal outside eval dir | Low | High | Validate resolved path is within `eval_ctx.eval_dir` before opening |
| Criteria templating breaks existing GEval judge configs with literal `{{` | Low | Medium | Only substitute keys present in the scenario context; unknown keys pass through unchanged |
