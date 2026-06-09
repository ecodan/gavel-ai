# Gavel-AI Parity Punch-List

> Comparison reference: Target Platform (ref/tfr). Gaps identified by reviewing README, AGENTS.md, README-JUDGES.md vs. gavel-ai canon and source tree.

---

## Summary of Key Differences

| Area | Target Platform | Gavel-AI | Gap                    |
|------|----------|----------|------------------------|
| Deterministic judges | ClassifierMetric + RegressionMetric | ✅ ClassifierMetric + RegressionMetric | Done                   |
| Built-in DeepEval judges | Toxicity, ConversationCompleteness, TurnRelevancy | ✅ All 4 types added | Done                   |
| Conversational judge | ConversationalGEval | ✅ Added to JUDGE_TYPE_MAP | Done                   |
| External judge configs | TOML + Markdown files | ✅ markdown_path + TOML loading | Done                   |
| Closed-box CLI | Full `closed-box` command group | Processor exists, no CLI | **Missing**            |
| Score scale | 0.0–1.0 | 1–10 integer | Diverged (intentional) |
| User simulation | 8 named personality types | Free-form tone string | **Missing**            |
| Autotune maturity | Full (per-iteration artifacts, convergence) | Beta | Done                   |
| Migration command | `<name> migrate` | None | **Missing**            |
| Conv granular steps | `conv generate` / `conv evaluate` | Partial (`generate` only; no `evaluate`/`report`) | **Partial**            |
| Scaffolding templates | `--template classification/regression` | ✅ Both templates implemented | Done                   |
| Schema docs | `schema-configs.md` + `schema-outputs.md` | ✅ Both docs authored | Done                   |
| Config snapshot | Full (includes prompts copy) | ✅ Prompts + snapshot_metadata.json | Done                   |
| Report: det. judge table | Separate table, prediction\|actual | ✅ Separate section in HTML report | Done                   |

---

## Punch-List

Items ordered by impact. Each item is self-contained and scoped to what is needed for parity.

---

### ✅ 1. Deterministic Judges (ClassifierMetric + RegressionMetric)

**Status**: Complete — `src/gavel_ai/judges/deterministic_metric.py` implements `ClassifierMetric` and `RegressionMetric`; both registered in `JudgeRegistry`.

**Gap (original)**: Target Platform provides zero-LLM-call judges for structured output evaluation using scikit-learn metrics. Gavel-AI has no equivalent.

**What to build**:
- `DeterministicJudge` base class in `judges/deterministic_judge.py`
- `ClassifierMetric` judge: per-sample score (1.0 if label matches, 0.0 otherwise), population metric via scikit-learn. Supported metrics: accuracy, f1, precision, recall, balanced_accuracy, matthews_corrcoef, cohen_kappa, jaccard, zero_one_loss, hamming_loss, fbeta.
- `RegressionMetric` judge: per-sample signed error, population metric via scikit-learn. Supported metrics: mean_absolute_error, mean_squared_error, root_mean_squared_error, median_absolute_error, max_error, r2_score, mean_absolute_percentage_error, explained_variance_score.
- Both require `prediction_field` (dotted path into structured JSON output) and `actual_field` (dotted path into scenario dict).
- Register both in `JudgeRegistry`.
- Skip with clear error if processor output is not a dict.
- Update scaffolding to support `--template classification` and `--template regression`.
- Add `scikit-learn` to dependencies.

**Config example**:
```json
{
  "name": "accuracy_judge",
  "type": "classifier",
  "prediction_field": "response",
  "actual_field": "expected",
  "report_metric": "accuracy"
}
```

---

### ✅ 2. Missing DeepEval Judge Types

**Status**: Complete — all 4 types added to `DeepEvalJudge.JUDGE_TYPE_MAP` in `deepeval_judge.py`. Conversational scaffold updated with `conversation_completeness` + `conversational_geval`.

**Gap (original)**: Gavel-AI's `JUDGE_TYPE_MAP` was missing: `ToxicityMetric`, `ConversationCompletenessMetric`, `ConversationalGEval`, and `TurnRelevancyMetric`.

**What to build**:
- Add to `DeepEvalJudge.JUDGE_TYPE_MAP`:
  - `"deepeval.toxicity"` → `ToxicityMetric`
  - `"deepeval.conversation_completeness"` → `ConversationCompletenessMetric`
  - `"deepeval.conversational_geval"` → `ConversationalGEval`
  - `"deepeval.turn_relevancy"` → `TurnRelevancyMetric`
- Update default conversational eval scaffold to include `conversation_completeness` + `conversational_geval` judges (matching Target Platform's defaults).
- Document thresholds in CLI help text: Toxicity/Hallucination: 0.85–0.95; AnswerRelevancy/Faithfulness: 0.65–0.80; ConversationCompleteness: 0.70–0.85.

---

### ✅ 3. External Judge Config Files (TOML + Markdown)

**Status**: Complete — `markdown_path` field on `JudgeConfig`; `_load_markdown_judge_config` helper in `judge_runner.py`; TOML `config` reference resolution also wired.

**Gap (original)**: Target Platform supports loading judge definitions from `config/judges/*.toml` and `config/judges/*.md` files. Gavel-AI only supported inline JSON judge config.

**What to build**:
- Support `"config"` field on a judge entry that references a TOML file at `config/judges/{name}.toml`. Fields: `criteria`, `evaluation_steps`, `threshold`.
- Support `"markdown_path"` field that references a Markdown file. Parse `## Criteria`, `## Evaluation Steps`, `## Threshold`, `## Guidelines` sections.
- Scaffold creates `config/judges/` directory with example TOML.
- Document in CLI help and user guide.

**TOML example** (`config/judges/quality_judge.toml`):
```toml
criteria = "Evaluate the clarity and helpfulness of the response"
evaluation_steps = [
    "Is the response relevant to the question?",
    "Is it clearly written?",
    "Does it provide actionable information?"
]
threshold = 0.7
```

---

### 4. Closed-Box CLI Command Group

**Gap**: `closedbox_processor.py` exists but there are no `gavel closed-box` CLI commands. Users cannot create, run, analyze, or report on closed-box evaluations from the CLI.

**What to build**:
- `src/gavel_ai/cli/commands/closedbox.py` with Typer app: `create`, `run`, `analyze`, `report`.
- `create`: scaffold eval directory with remote `eval_config.json`, `agents.json`, `scenarios.json`.
- `run`: invoke `ClosedBoxProcessor` via existing workflow infrastructure.
- `analyze`: compute performance metrics (avg latency, throughput, error rate, token usage) from `results_raw.jsonl`.
- `report`: generate HTML/Markdown from analyzed results.
- Register `app.add_typer(closedbox.app, name="closed-box")` in `cli/main.py`.

---

### 5. Autotune: Promote from Beta to Full

**Gap**: Autotune is labeled "beta" in the canon product overview. Target Platform's autotune is fully featured with per-iteration artifacts, a dedicated `create` command, constraint enforcement, and convergence options.

**What to build**:
- `autotune create` command (currently missing — only `run` and `report` exist).
- Per-iteration artifact directories: `runs/<timestamp>/iteration_{n}/` with raw and judged outputs.
- `autotune_metadata.json` artifact capturing: prompt versions, per-iteration scores, convergence reason.
- Constraint enforcement at validation time: warn if >1 model, >1 prompt, >3 judges, or >25 scenarios.
- Smart stopping: target score hit, max rounds, convergence threshold (default: improvement < 0.05), score degradation.
- `--verbose` flag for iteration-by-iteration progress output.
- Remove "Beta" label from product overview after completion.

---

### 6. Named User Personality Profiles for Conversational Eval

**Gap**: Target Platform has 8 named personality types (collaborative, resistant, confused, impatient, detail-oriented, creative, skeptical, goal-driven) with a `personality_distribution: "balanced"` config. Gavel-AI has a free-form `tone` string field, which is weaker and not enumerable.

**What to build**:
- `PersonalityType` enum in `models/conversation.py`: `collaborative`, `resistant`, `confused`, `impatient`, `detail_oriented`, `creative`, `skeptical`, `goal_driven`.
- `personality_distribution` field on `ConversationalConfig`: `"balanced"` (equal weight), `"challenging"` (heavier on resistant/confused/impatient), or a dict of weights.
- Update `TurnGenerator._build_turn_prompt` to inject personality-specific behavior instructions based on `personality_type`.
- Scaffold `conv create` to include `personality_distribution: "balanced"` in generated config.
- Keep existing `tone` field as a deprecated alias.

---

### 7. Granular Conversational CLI Steps

**Gap**: Target Platform exposes `conv generate` (scenarios), `conv generate --run` (conversations), `conv evaluate`, and `conv report` as separately invocable commands. Gavel-AI bundles everything in `conv run`. This prevents resumability and step-by-step control.

**What to build**:
- `gavel conv generate [--eval] [--num-scenarios N]` — generate scenarios only.
- `gavel conv generate [--eval] [--run <id>]` — generate conversations from existing scenarios.
- `gavel conv evaluate [--eval] [--run <id>]` — judge existing conversations.
- `gavel conv report [--eval] [--run <id>] [--format html|markdown]` — report only.
- `conv run` remains as the all-in-one shortcut (composes the above steps).
- `.workflow_status` file to track which steps are complete, enabling resume after interruption.

---

### ✅ 8. Config Snapshot: Include Prompts

**Status**: Complete — `LocalRunContext.snapshot_run_config()` copies `config/prompts/` to `.config/prompts/` and writes `snapshot_metadata.json`.

**Gap (original)**: `snapshot_run_config()` captured `eval_config.json`, `agents.json`, and `scenarios.json` but not prompt TOML files.

**What to build**:
- In `contexts.py::snapshot_run_config()`, also copy all files from `config/prompts/` to `.config/prompts/` in the run directory.
- Add `snapshot_metadata.json` to `.config/` recording what was snapshotted and when.
- Update the canon artifact directory diagram in `tech-overview.md`.

---

### ✅ 9. Schema Documentation

**Status**: Complete — `docs/specs/schema-configs.md` and `docs/specs/schema-outputs.md` authored and referenced from `CLAUDE.md`.

**Gap (original)**: No schema docs existed.

**What to build**:
- `docs/specs/schema-configs.md`: document `eval_config.json` (all fields, types, defaults), `agents.json` (`_models` structure, model parameters, provider_auth), `scenarios.json`, and judge config fields.
- `docs/specs/schema-outputs.md`: document `results_raw.jsonl`, `results_judged.jsonl`, run metadata, telemetry, and `.config/` snapshot structure.
- Reference these docs from `CLAUDE.md` as authoritative sources.

---

### 10. Migration Command

**Gap**: Target Platform provides `<name> migrate [--eval] [--dry-run]` to upgrade old eval configs to the current schema. As gavel-ai evolves, configs from early users will go stale. No migration path exists today.

**What to build**:
- `gavel migrate [--eval <name>] [--dry-run]` command.
- Detect current config schema version (default: unversioned = v1).
- Apply migration transforms sequentially (v1→v2, etc.).
- `--dry-run` shows what would change without writing.
- Add `config_schema` version field to `eval_config.json` (current: `"1.0"`).
- Document breaking changes between schema versions.

---

### ✅ 11. HTML Report: Deterministic Judge Table

**Status**: Complete — `DeterministicRunResult` model in `runtime.py`; `oneshot_reporter.py` routes deterministic results into a separate section, excluded from LLM average rollup.

**Gap (original)**: No deterministic judge section in the HTML report.

**What to build**:
- In `reporters/oneshot_reporter.py`, detect deterministic vs. LLM judges and route to separate `ReportData` sections.
- Jinja2 template: render deterministic judges in a separate table with `prediction | actual` columns.
- Exclude deterministic scores from the "LLM Avg" rollup calculation.
- Show skip reason inline when a judgment is skipped (e.g., "outputs is not a dict").

---

---

## OneShot Parity Breakdown

Detailed work items to bring `gavel oneshot` to full feature parity with Target Platform's oneshot workflow. Items ordered by dependency — earlier items unblock later ones.

---

### ✅ OS-1. Deterministic Judges: ClassifierMetric and RegressionMetric

**Status**: Complete — `src/gavel_ai/judges/deterministic_metric.py`; registered as `"classifier"` and `"regression"` in `JudgeRegistry`; batch-finalization hook in `judge_executor.py`.

**What was missing**: No deterministic judge implementations existed anywhere in the codebase.

**Files to create/modify**:
- Create `src/gavel_ai/judges/deterministic_judge.py`:
  - `DeterministicJudge(Judge)` base class — no LLM call, extracts values via dotted-path from `processor_output` (parsed as JSON dict) and `scenario` dict.
  - `ClassifierMetric(DeterministicJudge)`: per-sample score = 1.0 if string labels match (case-insensitive strip), else 0.0. Accumulates `(prediction, actual)` pairs. At batch end, computes population metric via scikit-learn. Supported `report_metric` values: `accuracy`, `f1`, `precision`, `recall`, `balanced_accuracy`, `matthews_corrcoef`, `cohen_kappa`, `jaccard`, `zero_one_loss`, `hamming_loss`, `fbeta` (requires `beta` field). Optional fields: `average` (binary/macro/micro/weighted), `positive_class`.
  - `RegressionMetric(DeterministicJudge)`: per-sample score = `float(prediction) - float(actual)` (signed error). Accumulates pairs. Population metric via scikit-learn. Supported `report_metric` values: `mean_absolute_error`, `mean_squared_error`, `root_mean_squared_error`, `median_absolute_error`, `max_error`, `r2_score`, `mean_absolute_percentage_error`, `explained_variance_score`.
  - Both skip with `{"skip_reason": "outputs is not a dict"}` if `processor_output` is not parseable JSON.
  - Both skip with `{"skip_reason": "prediction_field not found: <path>"}` if the dotted path doesn't resolve.
- Modify `src/gavel_ai/judges/judge_registry.py`: register `"classifier"` → `ClassifierMetric`, `"regression"` → `RegressionMetric`.
- Modify `src/gavel_ai/judges/judge_executor.py`: add batch-finalization hook so deterministic judges can compute their population metric after all per-sample calls complete.
- Add `scikit-learn` to `pyproject.toml` dependencies.
- Add unit tests in `tests/unit/judges/test_deterministic_judge.py`.

**Judge config fields** (added to `JudgeConfig` model in `models/config.py`):
```json
{
  "name": "accuracy_judge",
  "type": "classifier",
  "prediction_field": "response",
  "actual_field": "expected",
  "report_metric": "accuracy",
  "average": "macro"
}
```

---

### ✅ OS-2. External Judge Config Files (TOML)

**Status**: Complete — `get_judge_config()` on `LocalFileSystemEvalContext`; string `config` references resolved in `judge_runner.py`; example TOML written by scaffold.

**What was missing**: `config/judges/` was scaffolded as an empty directory; judge config had to be inline.

**Files to create/modify**:
- Modify `src/gavel_ai/core/contexts.py` (`LocalFileSystemEvalContext`): add `get_judge_config(name: str) -> dict` method that loads and parses `config/judges/{name}.toml`. Fields: `criteria`, `evaluation_steps`, `threshold`.
- Modify `src/gavel_ai/core/steps/judge_runner.py`: when a judge's `config` field is a string (not a dict), resolve it via `eval_ctx.get_judge_config(config_string)` before passing to the judge.
- Modify `src/gavel_ai/cli/scaffolding.py`: `generate_all_templates()` writes a `config/judges/quality_judge.toml` example file alongside the empty directory.
- Add unit tests covering string-reference resolution.

**TOML format** (`config/judges/quality_judge.toml`):
```toml
criteria = "Evaluate the quality and accuracy of the response"
evaluation_steps = [
    "Is the response relevant to the question?",
    "Is it clearly written?",
    "Does it provide actionable information?"
]
threshold = 0.7
```

---

### ✅ OS-3. Create Templates: `--template classification` and `--template regression`

**Status**: Complete — `--template` option on `oneshot create`; `_generate_classification_templates()` and `_generate_regression_templates()` in `scaffolding.py`.

**What was missing**: Only a single default scaffold; no classification or regression templates.

**Files to modify**:
- Modify `src/gavel_ai/cli/commands/oneshot.py` `create()`: add `--template` option (`default`, `classification`, `regression`).
- Modify `src/gavel_ai/cli/scaffolding.py`:
  - `generate_all_templates()` dispatch: route to `_generate_classification_templates()` or `_generate_regression_templates()` based on template flag.
  - **Classification template**: `eval_config.json` with `ClassifierMetric` judges (accuracy + f1), `scenarios.json` with 3 sample scenarios including one deliberately wrong `expected` value to verify error detection, `prompts/classifier.toml` with a prompt that returns structured JSON `{"response": "<label>"}`.
  - **Regression template**: `eval_config.json` with `RegressionMetric` judge (mean_absolute_error), `scenarios.json` with 3 numeric scenarios including one wrong expected, `prompts/regressor.toml` with a prompt that returns `{"response": <number>}`.
- Update `create()` help text to document available templates.

---

### ✅ OS-4. Config Snapshot: Include Prompts

**Status**: Complete — see item #8 above.

**What was missing**: `snapshot_run_config()` did not copy `config/prompts/*.toml`.

**Files to modify**:
- Modify `src/gavel_ai/core/contexts.py` `snapshot_run_config()`: after snapshotting the three existing files, also copy all files from `eval_ctx.eval_dir / "config" / "prompts"` into `{run_id}/.config/prompts/`. Skip silently if the directory doesn't exist.
- Optionally write a `{run_id}/.config/snapshot_metadata.json` listing what was captured and the snapshot timestamp.

---

### ✅ OS-5. Validator: Expand Pre-flight Checks

**Status**: Complete — variant→model resolution active; prompt file existence check at line 138; scenarios-not-empty enforced; structured `ValidationResult` with `errors` + `warnings`.

**What was missing**: Several checks were commented out or absent.

**Files to modify**:
- Modify `src/gavel_ai/core/steps/validator.py`:
  - **Re-enable variant resolution**: uncomment and fix the variant → model lookup (currently commented with "TODO"). Must handle both direct model names and agent references.
  - **Validate prompt files exist**: for each `test_subject.prompt_name` in `test_subjects`, call `eval_ctx.get_prompt(f"{name}:latest")` and surface a `ConfigError` with a clear message if not found.
  - **Validate judge types are registered**: for each judge in `test_subjects[*].judges`, call `JudgeRegistry.list_available()` and warn if the type is unregistered (warn not fail, to allow forward-compatible configs).
  - **Validate scenarios not empty**: the scenario count check is also commented out — re-enable with a `ValidationError` if the list is empty.
  - Emit a structured `ValidationResult` with both `errors` and `warnings` lists in all paths.

---

### ✅ OS-6. Step Completion Tracking (`.workflow_status`)

**Status**: Complete — `base.py:safe_execute()` calls `context.mark_step_complete()`; `LocalRunContext` writes JSONL `.workflow_status` and exposes `get_completed_steps()`; `StepPhase.PREPARE` written at run init.

**What was missing**: No step completion tracking existed.

**Files to modify**:
- Modify `src/gavel_ai/core/steps/base.py` `safe_execute()`: after a successful `execute()` call, call `context.mark_step_complete(self.phase)`.
- Modify `src/gavel_ai/core/contexts.py` `LocalRunContext`:
  - Add `mark_step_complete(phase: StepPhase)`: appends `{"step": phase.value, "completed_at": ISO8601}` to `{run_id}/.workflow_status` (JSONL format).
  - Add `get_completed_steps() -> list[StepPhase]`: reads `.workflow_status` and returns completed phases.
- Add `StepPhase.PREPARE = "prepare"` to the enum for the run initialization phase (written by `LocalRunContext.__init__()` after snapshot completes).
- Add unit tests covering status file creation and reading.

---

### ✅ OS-7. Error Output Exclusion from Score Averages

**Status**: Complete — `skipped_counts` tracked per variant/judge in `oneshot_reporter.py`; `None` and error scores excluded from averages; `(N skipped)` rendered in report template.

**What was missing**: All scores including errored results were averaged together.

**Files to modify**:
- Modify `src/gavel_ai/reporters/oneshot_reporter.py` `_build_context()`:
  - Skip a judgment entry from the running sum (and from the count) when `score` is `None`, `0` due to an error, or the result has a non-empty `error` field.
  - Add `skipped_count` per variant per judge to the context dict for display in the report.
- Modify `src/gavel_ai/reporters/templates/oneshot.html`: display `(N skipped)` next to any judge average that had exclusions.

---

### ✅ OS-8. Report: Deterministic Judge Section

**Status**: Complete — `DeterministicRunResult` + `PerSampleDeterministicResult` in `runtime.py`; reporter routes deterministic results out of LLM rollup; HTML template renders separate section.

**What was missing**: All judge results went through the same aggregation path.

**Files to modify**:
- Modify `src/gavel_ai/models/runtime.py` `ReportData`: add `deterministic_results: list[DeterministicJudgeResult]` field. `DeterministicJudgeResult` holds: `judge_name`, `report_metric`, `population_score`, `per_sample: list[{scenario_id, prediction, actual, score, skip_reason}]`.
- Modify `src/gavel_ai/reporters/oneshot_reporter.py` `_build_context()`:
  - Detect deterministic judges by checking `JudgeRegistry` type (or a `is_deterministic` flag on the judge).
  - Route their results into `report_data.deterministic_results` instead of `summary_metrics`.
  - Exclude deterministic scores from the LLM average rollup.
- Modify `src/gavel_ai/reporters/templates/oneshot.html`: add a "Deterministic Judges" section that renders `prediction | actual` columns per sample and the population metric value. Render after the LLM judge summary table.

---

### ✅ OS-9. In-Situ (Remote) `create` Scaffold

**Status**: Complete — `generate_eval_config()` branches on `eval_type == "in-situ"`, sets `test_subject_type: "in-situ"`, skips prompt template generation.

**What was missing**: `--type in-situ` was silently ignored; local scaffold was always generated.

**Files to modify**:
- Modify `src/gavel_ai/cli/scaffolding.py` `generate_eval_config()`: when `eval_type == "in-situ"`, set `"test_subject_type": "in-situ"` in the generated config and swap the `test_subjects[0]` to use a remote endpoint config structure instead of `prompt_name`.
- Modify `src/gavel_ai/cli/scaffolding.py` `generate_all_templates()`: skip generating `prompts/assistant.toml` for remote evals (no local prompt needed), and skip the prompt in `agents.json`.
- Update `--type` help text to reflect this.

---

### ✅ OS-10. Judge Criteria Templating Against Scenario Columns

**Status**: Complete — `_render_judge_template` + `_build_render_context` in `judge_runner.py`; applied to `criteria` and `evaluation_steps` at evaluation time; also applied to externally loaded TOML/Markdown configs.

**What was missing**: `criteria` and `evaluation_steps` strings were static; no per-scenario substitution. An `expected_output_template` exists for the expected-output field but does not extend to criteria or evaluation steps. This means judges cannot inline ground-truth values, category labels, or other per-scenario context into their rubric.

**What to build**:
- Add a `_render_template(template: str, context: dict) -> str` utility function (in a shared module or inline in `DeepEvalJudge`) that performs simple `{{key}}` substitution: for each `{{key}}` in the string, replace with `str(context[key])` if the key exists, leave unchanged if missing (no crash). No third-party templating library — plain regex or `str.replace`.
- In `DeepEvalJudge._create_metric()`, before passing `criteria` and `evaluation_steps` to `GEval`, call `_render_template()` on each string using the scenario context. The scenario context is not available at metric creation time — move criteria/evaluation_steps rendering to `_create_test_case()` or pass them through deferred rendering at `evaluate()` call time.
- Build the render context from `scenario.input` (if dict, unpack keys; if string, add as `input`) + `scenario.metadata` keys.
- On missing key: leave `{{key}}` in place, log a debug message.
- Update `GEvalConfig` docstring and scaffold help text to document the capability.
- Also apply rendering to `criteria` and `evaluation_steps` loaded from external TOML judge configs (OS-2).

**Example** — scenario row:
```json
{"scenario_id": "1", "input": "Classify this ticket", "metadata": {"expected_category": "billing"}}
```
Judge config:
```json
{
  "criteria": "Evaluate whether the response correctly identifies the category. Expected: {{expected_category}}",
  "evaluation_steps": ["Does the response match the expected category '{{expected_category}}'?"]
}
```
At evaluation time, `{{expected_category}}` is replaced with `"billing"` before the LLM judge call.

---
