# Canon Summary

> Auto-generated during canon synthesis. Consumed by agents at branch start.
> Target: 300–500 tokens. Optimize for density, not readability.

## Purpose

Provider-agnostic LLM evaluation framework for local/production benchmarking using CLI workflows.
Supports two evaluation modes: **OneShot** (single-turn prompt→response) and **Conversational** (multi-turn, multi-variant).

## Architecture

- **Clean Architecture**: Pluggable storage, judges, and providers using domain-driven patterns.
- **RunContext Lifecycle**: Immutable result storage (JSONL) managed via central state.
- **OTel Instrumentation**: Native OpenTelemetry spans for all execution and judge steps.
- **Local-First**: Filesystem-based artifacts for git-friendly history and reproducibility.
- **Step-based Workflows**: `OneShotWorkflow` and conversational flows compose discrete `Step` objects (Validator, Processor, JudgeRunner, ReportRunner).

## Modules

- `cli`: Presentation and command orchestration. `oneshot` subcommand has `create/run/judge/report/list/milestone`.
- `core`: Shared abstractions, models, step base classes, retry logic, exceptions.
  - `core/execution/retry_logic.py`: Async exponential-backoff retry helper.
  - `core/steps/conversational_processor.py`: Multi-turn, multi-variant conversation execution with `max_turns` and `max_duration_ms` enforcement.
- `processors`: Domain logic for OneShot, Conversational, and Autotune.
- `judges`: Evaluation logic and adapters for GEval/DeepEval, plus `DeterministicMetric` subclasses (`ClassifierMetric`, `RegressionMetric`) for GT-comparison without an LLM call. Registered as `"classifier"`/`"regression"` in `JudgeRegistry`; routed by `JudgeRunnerStep` to a separate synchronous loop. No standalone re-judge class; use `gavel oneshot judge`.
- `reporters`: Jinja2-based HTML/Markdown reports. `OneShotReporter` maps results to Unified ReportData (1-turn conversation model).
- `storage`: Persistence interface and filesystem implementation.
- `providers`: Provider-agnostic factory using Pydantic-AI.
- `conversational/errors.py`: Error hierarchy (`ConversationalError`, `TurnGenerationError`, `RateLimitError`, `AuthError`) with `classify_error()`.

## Conventions

- **Snake case**: Mandatory for code, config fields, and telemetry attributes.
- **Span emission**: LLM calls and judge evaluations must emit OTel spans.
- **Immutability**: `results_raw.jsonl` remains unchanged after final processor exit.
- **OutputRecord as pipeline type**: `ScenarioProcessorStep` emits `List[OutputRecord]` into `context.processor_results`. `JudgeRunnerStep` groups by `variant_id` (not by zip position). `ReportRunnerStep` joins by `(scenario_id, variant_id)`.
- **No ResultsExporter/ReJudge**: Deleted. Hash utility lives in `storage/utils.py::compute_config_hash`.
- **Judge config**: Use `name` and `type` fields (not `id`/`judge_type`). Registered via `JudgeRegistry`. Set `config_ref: "name"` to load external TOML from `config/judges/{name}.toml` (resolved by `JudgeRunnerStep`).
- **Deterministic metrics**: `type: "classifier"` or `type: "regression"` in judge config routes to `DeterministicMetric` (scikit-learn GT-comparison, no LLM). Results in `context.deterministic_metrics` → `ReportData.deterministic_results`. Never written to JSONL result files.
- **Step tracking**: `Step.safe_execute()` writes completed phase to `{run_dir}/.workflow_status` (JSONL). `StepPhase.PREPARE` written on `LocalRunContext` init.
- **Snapshot**: `snapshot_run_config()` copies prompts to `.config/prompts/` and writes `snapshot_metadata.json`.
- **Validator gates**: Variant resolution and prompt existence checks are gated on `test_subject_type == "local"`. In-situ evals skip them.
- **Scaffold templates**: `gavel oneshot create --template classification|regression` generates deterministic-judge eval configs.
- **Duration fields**: `max_duration_ms` (ms, 30000–3600000) in `ConversationalConfig`; `timing_ms` on results.
- **Test markers**: All tests tagged `@pytest.mark.unit` or `@pytest.mark.integration`. Run with `pytest -m unit` / `pytest -m integration`.
