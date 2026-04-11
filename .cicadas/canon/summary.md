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
- `judges`: Evaluation logic and adapters for GEval/DeepEval. `ReJudge` supports re-running judges on existing `results_raw.jsonl`.
- `reporters`: Jinja2-based HTML/Markdown reports. `OneShotReporter` maps results to Unified ReportData (1-turn conversation model).
- `storage`: Persistence interface and filesystem implementation.
- `providers`: Provider-agnostic factory using Pydantic-AI.
- `conversational/errors.py`: Error hierarchy (`ConversationalError`, `TurnGenerationError`, `RateLimitError`, `AuthError`) with `classify_error()`.

## Conventions

- **Snake case**: Mandatory for code, config fields, and telemetry attributes.
- **Span emission**: LLM calls and judge evaluations must emit OTel spans.
- **Immutability**: `results_raw.jsonl` remains unchanged after final processor exit.
- **Judge config**: Use `name` and `type` fields (not `id`/`judge_type`). Registered via `JudgeRegistry`.
- **Duration fields**: `max_duration_ms` (ms, 30000–3600000) in `ConversationalConfig`; `timing_ms` on results.
- **Test markers**: All tests tagged `@pytest.mark.unit` or `@pytest.mark.integration`. Run with `pytest -m unit` / `pytest -m integration`.
