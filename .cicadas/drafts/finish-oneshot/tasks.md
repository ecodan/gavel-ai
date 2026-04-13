
---
summary: "Three partitions. P1 (deterministic-metrics) and P2 (pipeline-hardening) are parallel. P3 (report-scaffold-toml) is sequential after both merge. No feature PRs. One initiative PR to master at the end."
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
  - "src/gavel_ai/judges"
  - "src/gavel_ai/core/steps"
  - "src/gavel_ai/core/contexts.py"
  - "src/gavel_ai/cli"
  - "src/gavel_ai/reporters"
  - "src/gavel_ai/models"
index:
  partition_one: "## Partition: feat/deterministic-metrics"
  partition_two: "## Partition: feat/pipeline-hardening"
  partition_three: "## Partition: feat/report-scaffold-toml"
  initiative_boundary: "## Initiative Boundary"
next_section: "## Partition: feat/deterministic-metrics"
---

# Tasks: finish-oneshot

## Partition: feat/deterministic-metrics

- [ ] Add `PerSampleDeterministicResult` and `DeterministicRunResult` Pydantic models to `src/gavel_ai/models/runtime.py` <!-- id: 1 -->
- [ ] Create `src/gavel_ai/judges/deterministic_metric.py`: `DeterministicMetric(ABC)` base class with `__init__`, abstract `evaluate_sample()`, and abstract `compute()`; include dotted-path utility function `_resolve_path(obj, dotted_key)` <!-- id: 2 -->
- [ ] Implement `ClassifierMetric(DeterministicMetric)`: case-insensitive label match → `match: bool`; accumulate per-sample data; `compute()` calls scikit-learn metric from `report_metric` field <!-- id: 3 -->
- [ ] Implement `RegressionMetric(DeterministicMetric)`: unbounded signed error `float(prediction) - float(actual)` → `raw_score`; accumulate pairs; `compute()` calls scikit-learn metric <!-- id: 4 -->
- [ ] Add skip-on-invalid-output logic to both metrics: non-JSON `processor_output` → `skip_reason="outputs is not a dict"`; missing `prediction_field` path → `skip_reason="prediction_field not found: <path>"`; missing `actual_field` path → `skip_reason="actual_field not found: <path>"`; `compute()` excludes skipped entries and returns `population_score=None` when all skipped <!-- id: 5 -->
- [ ] Add `ClassifierMetric.__init__` validation: raise `ConfigError` if `report_metric == "fbeta"` and `beta` is absent from config <!-- id: 6 -->
- [ ] Add module-level registration at bottom of `deterministic_metric.py`: `JudgeRegistry.register("classifier", ClassifierMetric)` and `JudgeRegistry.register("regression", RegressionMetric)` <!-- id: 7 -->
- [ ] Confirm `JudgeRegistry.create()` has no type narrowing that assumes the returned instance is a `Judge`; fix if present <!-- id: 8 -->
- [ ] Add `scikit-learn>=1.4,<2.0` to `pyproject.toml` dependencies; verify install with `pip install -e .` <!-- id: 9 -->
- [ ] Modify `src/gavel_ai/core/steps/judge_runner.py`: import `DeterministicMetric`; after building `judges_list`, partition into `llm_configs` and `det_configs`; pass `llm_configs` to `JudgeExecutor` as before; add inline loop for `det_configs` that instantiates each metric, calls `evaluate_sample()` per record in scenario order, then calls `compute()`; store all results in `context.deterministic_metrics: Dict[str, DeterministicRunResult]` <!-- id: 10 -->
- [ ] Write `tests/unit/judges/test_deterministic_metric.py`: cover match/mismatch, case-insensitivity, unbounded regression error, all three skip conditions, `population_score=None` when all skipped, correct `accuracy` for known 3-sample fixture, correct `mean_absolute_error` for known numeric fixture, `fbeta` missing beta raises `ConfigError`, registry returns correct types <!-- id: 11 -->
- [ ] Write integration test confirming `JudgeRunnerStep` sets `context.deterministic_metrics` correctly when a mix of LLM and deterministic judge configs are present; confirm `context.evaluation_results` is still populated for LLM judges <!-- id: 12 -->
- [ ] Run `pytest -m unit` and `pytest -m integration` — all pass <!-- id: 13 -->

## Partition: feat/pipeline-hardening

- [ ] Spike: check `pyproject.toml` `requires-python`; if `< 3.11`, add `tomli` as a conditional dependency and write a `_tomllib` import shim; document the decision in a comment <!-- id: 20 -->
- [ ] Add `StepPhase.PREPARE = "prepare"` to the enum in `src/gavel_ai/core/steps/base.py` <!-- id: 21 -->
- [ ] Add abstract methods `mark_step_complete(phase: StepPhase) -> None` and `get_completed_steps() -> List[StepPhase]` to `RunContext` ABC in `src/gavel_ai/core/contexts.py` <!-- id: 22 -->
- [ ] Implement `mark_step_complete()` on `LocalRunContext`: append `{"step": phase.value, "completed_at": ISO8601}` to `{run_dir}/.workflow_status` (JSONL, append-only, create on first write) <!-- id: 23 -->
- [ ] Implement `get_completed_steps()` on `LocalRunContext`: read `.workflow_status` and return list of `StepPhase` values in order; return `[]` if file does not exist <!-- id: 24 -->
- [ ] Modify `LocalRunContext.__init__()`: after `snapshot_run_config()` completes, call `self.mark_step_complete(StepPhase.PREPARE)` <!-- id: 25 -->
- [ ] Modify `Step.safe_execute()` in `base.py`: on successful `execute()`, call `context.mark_step_complete(self.phase)` before returning `True` <!-- id: 26 -->
- [ ] Extend `LocalRunContext.snapshot_run_config()`: after snapshotting the three existing files, copy all files from `eval_ctx.config_dir / "prompts"` into `{run_dir}/.config/prompts/` using `shutil.copytree` (skip silently if source does not exist) <!-- id: 27 -->
- [ ] Write `{run_dir}/.config/snapshot_metadata.json` at the end of `snapshot_run_config()`: `{"snapshotted_at": ISO8601, "files": [list of relative paths copied]}` <!-- id: 28 -->
- [ ] Add `get_judge_config(name: str) -> Dict[str, Any]` to `LocalFileSystemEvalContext`: load `config/judges/{name}.toml` via `tomllib`; cache in `self._judge_config_cache: Dict[str, Dict]`; raise `ConfigError` (not `FileNotFoundError`) when file is absent; return parsed dict <!-- id: 29 -->
- [ ] Modify `ValidatorStep`: re-enable variant resolution block; gate on `eval_config.test_subject_type == "local"`; check each variant resolves to a model directly or via an agent reference; raise `ConfigError` with clear message on failure <!-- id: 30 -->
- [ ] Modify `ValidatorStep`: add prompt existence check; gate on `test_subject_type == "local"`; for each `test_subject.prompt_name`, call `eval_ctx.get_prompt(f"{name}:latest")`; raise `ConfigError` with path if missing <!-- id: 31 -->
- [ ] Modify `ValidatorStep`: add judge type warning; for each judge in all test subjects, call `JudgeRegistry.list_available()`; log `WARNING` if judge type is not registered (do not raise) <!-- id: 32 -->
- [ ] Modify `ValidatorStep`: re-enable scenario count check; after loading scenarios, raise `ValidationError` if list is empty <!-- id: 33 -->
- [ ] Ensure `ValidatorStep` emits a structured `ValidationResult(is_valid, errors, warnings)` in all code paths (including early-exit paths) <!-- id: 34 -->
- [ ] Write `tests/unit/core/test_step_tracking.py`: cover `.workflow_status` creation, `PREPARE` entry on init, step entry on `safe_execute` success, no entry on failure, `get_completed_steps` returns correct order, returns `[]` when file absent <!-- id: 35 -->
- [ ] Write `tests/unit/core/test_contexts_snapshot.py`: cover prompts copied to `.config/prompts/`, `snapshot_metadata.json` written with correct fields, silent skip when `config/prompts/` absent, `get_judge_config` returns dict, `get_judge_config` raises `ConfigError` on missing file <!-- id: 36 -->
- [ ] Write `tests/unit/core/test_validator_expanded.py`: cover variant resolution (direct model, agent reference, unknown raises), prompt missing raises, unregistered judge type warns, empty scenarios raises, valid config passes with no errors <!-- id: 37 -->
- [ ] Run `pytest -m unit` — all pass <!-- id: 38 -->

## Partition: feat/report-scaffold-toml

- [ ] Add `deterministic_results: List[DeterministicRunResult] = Field(default_factory=list)` to `ReportData` in `src/gavel_ai/models/runtime.py` (extends P1's changes already on the initiative branch) <!-- id: 40 -->
- [ ] Add `raw_results: List[Dict[str, Any]] = field(default_factory=list)` and `deterministic_metrics: Optional[Dict[str, Any]] = None` fields to `RunData` dataclass in `src/gavel_ai/core/steps/report_runner.py` <!-- id: 41 -->
- [ ] Modify `ReportRunnerStep.execute()`: pass `processor_results` as `raw_results` and `getattr(run_context, "deterministic_metrics", None)` as `deterministic_metrics` when constructing `RunData` <!-- id: 42 -->
- [ ] Modify `src/gavel_ai/core/steps/judge_runner.py`: before instantiating `JudgeExecutor`, loop over `judges_list`; for each config where `config.config_ref` is set, call `context.eval_context.get_judge_config(config.config_ref)` and merge the result into `config.config`; raise `ConfigError` with user-facing message if TOML file is missing (extends P1's changes to `judge_runner.py`) <!-- id: 43 -->
- [ ] Modify `OneShotReporter._build_context()`: build `processor_errors: Dict[Tuple[str,str], bool]` from `run.raw_results`; skip a judge score entry from sum/count when the corresponding key is in `processor_errors`; track `skipped_count: Dict[Tuple[str,str], int]` per `(variant, judge_name)` <!-- id: 44 -->
- [ ] Modify `OneShotReporter._build_context()`: if `run.deterministic_metrics` is not None, populate `report_data.deterministic_results` from each `DeterministicRunResult` in the dict <!-- id: 45 -->
- [ ] Extend `src/gavel_ai/reporters/templates/oneshot.html`: add `(N skipped)` annotation (muted text) next to any judge average where `skipped_count > 0` for that `(variant, judge)` pair <!-- id: 46 -->
- [ ] Extend `oneshot.html`: add "Deterministic Judges" section after the LLM judge summary table; render per-metric subsections; classifier columns: `Scenario | Prediction | Actual | Match`; regression columns: `Scenario | Prediction | Actual | Signed Error`; show population metric name + value below each table; show `N/A (0 samples)` when `population_score` is None; skip section entirely when `deterministic_results` is empty <!-- id: 47 -->
- [ ] Add `--template` `typer.Option` to `create()` in `src/gavel_ai/cli/commands/oneshot.py`; default `"default"`; help text lists `default`, `classification`, `regression`; pass through to `generate_all_templates()` <!-- id: 48 -->
- [ ] Modify `src/gavel_ai/cli/scaffolding.py` `generate_all_templates()`: accept `template: str = "default"` arg; dispatch to `_generate_classification_templates()` or `_generate_regression_templates()` when appropriate; fall through to existing default path for `"default"` <!-- id: 49 -->
- [ ] Implement `_generate_classification_templates()` in `scaffolding.py`: write `eval_config.json` with `ClassifierMetric` judges (`accuracy` + `f1`, `prediction_field: "label"`, `actual_field: "expected"`), `scenarios.json` with 3 samples including one wrong expected, `prompts/classifier.toml` with a prompt that returns JSON `{"label": "<class>"}` <!-- id: 50 -->
- [ ] Implement `_generate_regression_templates()` in `scaffolding.py`: write `eval_config.json` with `RegressionMetric` judge (`mean_absolute_error`, `prediction_field: "value"`, `actual_field: "expected"`), `scenarios.json` with 3 numeric samples including one wrong expected, `prompts/regressor.toml` with a prompt that returns JSON `{"value": <number>}` <!-- id: 51 -->
- [ ] Add example `config/judges/quality_judge.toml` generation to all scaffold paths (default, classification, regression) <!-- id: 52 -->
- [ ] Fix `generate_eval_config()` for `eval_type == "in-situ"`: set `"test_subject_type": "in-situ"`; use remote endpoint structure for `test_subjects[0]` (replace `prompt_name` with `system_id`, `protocol`, `config` fields) <!-- id: 53 -->
- [ ] Fix `generate_all_templates()` for `eval_type == "in-situ"`: skip `generate_prompts_toml()` call; skip agent prompt key in `agents.json`; update `--type` help text to document the behavioral difference <!-- id: 54 -->
- [ ] Write unit tests for reporter changes: fixture with 1 error out of 3 produces correct average over 2 samples; `(1 skipped)` appears in rendered HTML; deterministic section renders with correct columns; section absent when `deterministic_results` is empty <!-- id: 55 -->
- [ ] Write unit tests for scaffold: `--template classification` produces `eval_config.json` with `type: "classifier"` judge; `--template regression` produces `type: "regression"` judge; `--type in-situ` produces `test_subject_type: "in-situ"` and no `prompts/` dir; unknown `--template` value exits non-zero <!-- id: 56 -->
- [ ] Write unit test: `config_ref` resolution loads TOML and merges into `judge_config.config`; missing TOML raises `ConfigError` with correct message <!-- id: 57 -->
- [ ] Run `pytest -m unit` and `pytest -m integration` — all pass <!-- id: 58 -->

## Initiative Boundary

- [ ] Open PR: initiative/finish-oneshot → master and await merge approval before continuing <!-- id: 100 -->
