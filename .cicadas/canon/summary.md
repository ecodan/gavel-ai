# Canon Summary

> Auto-generated during canon synthesis. Consumed by agents at branch start.
> Target: 300–500 tokens. Optimize for density, not readability.

## Purpose

Provider-agnostic LLM evaluation framework for local/production benchmarking using CLI workflows.
Supports two evaluation modes: **OneShot** (single-turn prompt→response) and **Conversational** (multi-turn, multi-variant).

## Architecture

- **Clean Architecture**: Pluggable storage, judges, and providers using domain-driven patterns.
- **RunContext Lifecycle**: Immutable result storage (JSONL) managed via central state. `RunContext.last_step_error` holds the triggering exception from the last failed step (set by `Step.safe_execute()`).
- **Error Policy**: `EvalConfig.error_policy` (`ErrorPolicy` model: `exit_on_error=True`, `exit_on_warning=False`) controls fail-fast behaviour. `core/issue_classifier.py::classify(exc)` maps to `ERROR`/`WARNING`/`OK`. `RunPolicyError` is raised immediately when threshold exceeded; never re-wrapped by `safe_execute`.
- **OTel Instrumentation**: Native OpenTelemetry spans for all execution and judge steps.
- **Local-First**: Filesystem-based artifacts for git-friendly history and reproducibility.
- **Step-based Workflows**: `OneShotWorkflow` and conversational flows compose discrete `Step` objects (Validator, Processor, JudgeRunner, ReportRunner).

## Modules

- `cli`: Presentation and command orchestration. Root `gavel init` command writes `.gavel/config.json`; all eval commands emit a soft warning if config absent. `oneshot` subcommand has `create/run/judge/report/list/milestone`. `cli/common.py` provides `resolve_eval_root(str|None) → Path` (4-tier: CLI flag → `GAVEL_EVAL_ROOT` env → `.gavel/config.json` → `.gavel/evaluations`) and `run_async()`. Run errors displayed as Rich panel (human-readable + log path) — full stack trace stays in `run.log`.
- `core`: Shared abstractions, models, step base classes, retry logic, exceptions.
  - `core/execution/retry_logic.py`: Async exponential-backoff retry helper.
  - `core/steps/conversational_processor.py`: Multi-turn, multi-variant conversation execution with `max_turns` and `max_duration_ms` enforcement.
  - `core/steps/scenario_processor.py`: Validates prompt `$var` placeholders against scenario fields at run-start (local evals only); renders templates via `string.Template`.
- `processors`: Domain logic for OneShot, Conversational, and Autotune.
- `judges`: Evaluation logic and adapters for GEval/DeepEval, plus `DeterministicMetric` subclasses (`ClassifierMetric`, `RegressionMetric`) for GT-comparison without an LLM call. Registered as `"classifier"`/`"regression"` in `JudgeRegistry`; routed by `JudgeRunnerStep` to a separate synchronous loop. No standalone re-judge class; use `gavel oneshot judge`.
- `reporters`: Jinja2-based HTML/Markdown reports. `OneShotReporter` maps results to Unified ReportData (1-turn conversation model). `_build_context()` injects: `total_execution_time_s` (from `run.telemetry["total_duration_seconds"]`, None if absent), `input_source` (from `RunData.metadata`), `subject_names` (list, falls back to unique `test_subject` values from scenario map), `scenario_count`, `input_collapse_threshold` (200 chars), `response_truncate_threshold` (500 chars). Template (`oneshot.html`) renders: split LLM/deterministic judge sections, per-subject sub-headings in Eval Summary and Performance, table layout for Scenario Detail, collapsible inputs, truncatable responses.
- `storage`: Persistence interface and filesystem implementation.
- `providers`: Provider-agnostic factory using Pydantic-AI. Token extraction uses `input_tokens`/`output_tokens` (pydantic-ai `RunUsage` fields); timing stored as `total_latency_ms` in aggregated metadata.
- `conversational/errors.py`: Error hierarchy (`ConversationalError`, `TurnGenerationError`, `RateLimitError`, `AuthError`) with `classify_error()`.

## Conventions

- **Snake case**: Mandatory for code, config fields, and telemetry attributes.
- **Span emission**: LLM calls and judge evaluations must emit OTel spans.
- **Immutability**: `results_raw.jsonl` remains unchanged after final processor exit.
- **OutputRecord as pipeline type**: `ScenarioProcessorStep` emits `List[OutputRecord]` into `context.processor_results`. `JudgeRunnerStep` groups by `variant_id` (not by zip position). `ReportRunnerStep` joins by `(scenario_id, variant_id)` and injects `input_source` (formatted as `"{source} ({name})"` from `eval_config.scenarios`) and `subject_names` (from `test_subjects[*].prompt_name`, falling back to unique `test_subject` values from `processor_results`) into `RunData.metadata`.
- **No ResultsExporter/ReJudge**: Deleted. Hash utility lives in `storage/utils.py::compute_config_hash`.
- **Judge config**: Use `name` and `type` fields (not `id`/`judge_type`). Registered via `JudgeRegistry`. Set `config_ref: "name"` to load external TOML from `config/judges/{name}.toml`. Set `markdown_path: "path/to/file.md"` (relative to eval dir) to load criteria, evaluation_steps, threshold, and guidelines from a markdown file. Criteria and `evaluation_steps` items support `{{key}}` template substitution using scenario fields at run time.
- **Prompt templates**: Use `$var` or `${var}` syntax (Python `string.Template`) in `.toml` prompt files — not `{{var}}`. Placeholders validated against scenario fields at run-start.
- **DeepEval judge types**: `deepeval.geval`, `deepeval.hallucination`, `deepeval.answer_relevancy`, `deepeval.faithfulness`, `deepeval.contextual_precision`, `deepeval.contextual_recall`, `deepeval.contextual_relevancy`, `deepeval.toxicity`, `deepeval.conversation_completeness`, `deepeval.conversational_geval`, `deepeval.turn_relevancy`. Recommended thresholds: Toxicity 0.85–0.95; ConversationCompleteness 0.70–0.85; AnswerRelevancy/Faithfulness 0.65–0.80.
- **Deterministic metrics**: `type: "classifier"` or `type: "regression"` in judge config routes to `DeterministicMetric` (scikit-learn GT-comparison, no LLM). Results in `context.deterministic_metrics` → `ReportData.deterministic_results`. Never written to JSONL result files.
- **Step tracking**: `Step.safe_execute()` writes completed phase to `{run_dir}/.workflow_status` (JSONL). `StepPhase.PREPARE` written on `LocalRunContext` init.
- **Snapshot**: `snapshot_run_config()` copies prompts to `.config/prompts/` and writes `snapshot_metadata.json`.
- **Validator gates**: Variant resolution and prompt existence checks are gated on `test_subject_type == "local"`. In-situ evals skip them.
- **Scaffold templates**: `gavel oneshot create --template classification|regression` generates deterministic-judge eval configs. Scaffolded `field_mapping.expected_output` defaults to `"expected"` (matching default scenario field name).
- **Duration fields**: `max_duration_ms` (ms, 30000–3600000) in `ConversationalConfig`; `timing_ms` on results.
- **Schema docs**: `docs/specs/schema-configs.md` and `docs/specs/schema-outputs.md` document all config and output schemas.
- **Test markers**: All tests tagged `@pytest.mark.unit` or `@pytest.mark.integration`. Run with `pytest -m unit` / `pytest -m integration`.
- **Eval root (Annotated pattern)**: All CLI command functions use `eval_root: Annotated[Optional[str], typer.Option("--eval-root", envvar="GAVEL_EVAL_ROOT", ...)] = None`. The `= None` default is required so direct Python calls (unit tests) receive `None`, not Typer's `OptionInfo` object.
- **Packaging**: `pyproject.toml` uses `[tool.setuptools.packages.find] where = ["src"]` and `[tool.setuptools.package-data] gavel_ai = ["reporters/templates/*"]` for correct `pip install` / `uv add` behavior from external projects.
