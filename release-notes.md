# Release Notes

## 0.2.3

- **Breaking**: Judge scores (`JudgeResult`, `JudgeEvaluation`, `JudgedRecord.score`) are now `float` on a **0.0-1.0 scale**, replacing the manufactured 1-10 integer scale. DeepEval and external/custom judge scores pass through natively (clamped to [0.0, 1.0]) instead of being remapped via `1 + raw*9`. Anything reading `results_judged.jsonl` or `judge.score` directly should expect 0.0-1.0 floats going forward.
- **Fix**: Fixed a latent double-normalization bug in Autotune — `TuneStep._compute_avg_score()` had its own hardcoded `/10.0` independent of `core/autotune/scoring.py::normalize_score()`, which would have silently produced scores 10x too small once the underlying judge score became native 0.0-1.0.

## 0.2.2

- **Fix**: `gavel --version` now reads the installed package version via `importlib.metadata` instead of a hardcoded string, so it no longer drifts from `pyproject.toml`.

## 0.2.1

- **Feature**: `deepeval.geval` judge config now supports `evaluation_params` — a list restricting which `LLMTestCase` fields (`input`, `actual_output`, `expected_output`, `context`, `retrieval_context`) are sent to the judge LLM. Defaults to all of `input`, `actual_output`, `expected_output` (previous behaviour). Useful for omitting large `input` payloads (e.g. full page HTML) from judge calls when criteria only compares output to golden, reducing judge token cost. Invalid entries raise `JudgeError` with the list of valid options.

## 0.2.0

- **Feature**: Three-tier issue classifier (`ERROR` / `WARNING` / `OK`) and `error_policy` on `EvalConfig`. Set `error_policy.exit_on_error: false` to let scenarios with LLM 4xx/5xx errors be recorded and skipped rather than aborting the run; set `exit_on_warning: true` for fail-fast on schema/config validation issues. Defaults preserve existing behaviour (`exit_on_error: true`, `exit_on_warning: false`). `RunPolicyError` is raised immediately on threshold breach (fail-fast, not batched). New module `core/issue_classifier.py` with `classify(exc)` and `classify_message(msg)`.
- **Feature**: `EvalConfig.error_policy` (`ErrorPolicy` model) wired into `OneShotWorkflow` and threaded to all steps via `safe_execute(error_policy=...)`. `Step.safe_execute()` now re-raises `RunPolicyError` without re-wrapping; `ErrorPolicy.should_halt(tier)` centralises the halt predicate.
- **Feature**: `gavel init [--eval-root DIR] [--force]` command initializes a project by writing `.gavel/config.json` with the chosen eval root. Idempotent; `--force` overwrites. All eval-touching commands emit a soft yellow warning to stderr if config is absent.
- **Feature**: 4-tier eval root resolution via `resolve_eval_root()` in `cli/common.py`: explicit `--eval-root` flag → `GAVEL_EVAL_ROOT` env var → `.gavel/config.json` → `.gavel/evaluations` default. All `oneshot` and `conv` commands accept `--eval-root` (with `GAVEL_EVAL_ROOT` envvar) using the `Annotated` pattern so direct Python calls in tests receive `None` rather than Typer's `OptionInfo` object.
- **Fix**: `pyproject.toml` now declares `[tool.setuptools.packages.find] where = ["src"]` and `[tool.setuptools.package-data] gavel_ai = ["reporters/templates/*"]` so `pip install gavel-ai` / `uv add gavel-ai` from an external project correctly includes all modules and Jinja2 report templates.
- **Fix**: Removed `exc_info=True` from app-logger error calls in `Step.safe_execute()` and `OneShotWorkflow.execute()`. The run-logger already captures the full trace; the duplicate caused stack traces to appear in the terminal.
- **Fix**: Removed unsupported `cost_per_input_token` / `cost_per_output_token` kwargs from `GeminiModel` and `OllamaModel` constructors in `deepeval_judge.py`. Those constructors do not accept cost arguments, causing a `TypeError` on judge runs.
- **Fix**: OTel tracer init in `spans.py` now checks `isinstance(current_global, trace.ProxyTracerProvider)` before calling `set_tracer_provider()`, replacing a broad `try/except`. Prevents the "Overriding of current TracerProvider is not allowed" warning when gavel-ai is used as a library inside a host app that already initialised OTel.

- **Feature**: 4 new DeepEval judge types added to `JUDGE_TYPE_MAP`: `deepeval.toxicity`, `deepeval.conversation_completeness`, `deepeval.conversational_geval`, `deepeval.turn_relevancy`. CLI threshold help text updated with recommended ranges per type.
- **Feature**: Judge config supports `markdown_path` — a path relative to the eval dir pointing to a Markdown file with `## Criteria`, `## Evaluation Steps`, `## Threshold`, and `## Guidelines` sections. Merged after `config_ref` resolution; path traversal rejected with `ConfigError`.
- **Feature**: Judge `criteria` strings and `evaluation_steps` list items support `{{key}}` template substitution using scenario fields, resolved at run time by `JudgeRunnerStep._render_judge_template()`.
- **Feature**: `ScenarioProcessorStep` validates `$var` prompt placeholders against scenario fields at run-start for `local` evals, raising `ConfigError` early rather than sending literal placeholder text to the LLM.
- **Feature**: CLI run failures display a Rich panel to stderr with the human-readable cause and the exact path to `run.log`. Full stack traces remain in `run.log` only.
- **Fix**: Scaffolded prompt templates now use `$var` / `${var}` syntax (Python `string.Template`) instead of `{{var}}`. The previous Jinja-style placeholders were never substituted.
- **Fix**: Scaffolded `eval_config.json` `field_mapping.expected_output` now defaults to `"expected"`, matching the default scenario field name. Previously defaulted to `"expected_behavior"`, causing GEval to fail at judging.
- **Fix**: `ProviderFactory` now reads `response.usage.input_tokens` / `output_tokens` (pydantic-ai `RunUsage` fields) for token counts. Previously read `prompt_tokens`/`completion_tokens` which are not present in pydantic-ai responses, resulting in zero token counts.
- **Fix**: `OutputRecord.timing_ms` now populated from `metadata["total_latency_ms"]` (the key written by `PromptInputProcessor`). Previously read `"latency_ms"`, which is only set at the individual call level before aggregation.
- **Docs**: Added `docs/specs/schema-configs.md` and `docs/specs/schema-outputs.md` with full field-level documentation for all config and output schemas.
- **Feature**: `deepeval.geval` judges now support `scenarios.field_mapping` — an optional object on the `scenarios` config section that maps scenario file fields (using dot notation) to GEval test-case params (`input`, `expected_output`, `actual_output`). Configured once per eval; applies to all GEval judges in the run. Gavel validates all scenarios can resolve `expected_output` before any API call and raises `ConfigError` upfront with scenario IDs if any are missing.
- **Feature**: `deepeval.geval` judge config now supports `strict_mode: true` to return a binary 0/1 score (normalizes to 1 or 10) instead of a continuous score. Useful for hard pass/fail checks (schema compliance, format validation).
- **Model**: `Scenario` now accepts `expected_output` as an explicit field alongside `expected_behavior` / `expected`. Recognized by `_resolve_field` dot-notation traversal and used as a final fallback in `_get_expected_output`.
- **Tests**: Added unit tests for `_resolve_scenario_field`, `_validate_geval_expected_output`, GEval field_mapping resolution, and `strict_mode` forwarding.
- **Tests**: Added end-to-end integration test suite for the OneShot pipeline (`tests/integration/test_oneshot_pipeline_e2e.py`). Covers happy-path scenario processing, prompt version resolution (`latest` and pinned), output record validation, and error cases (missing prompt file, missing variant, empty scenario list).
- **Skills**: Added Claude Code skills `gavel-skill` (gavel-ai evaluation guidance) and `update-docs` (pre-commit documentation sync) under `.claude/skills/`.
- **Chore**: Extended `.gitignore` to exclude `/context.md`, `/ref/`, and `/coverage_reports/`.
- **Cicadas**: Improved `scan_repo.py` SDD tool-state directory exclusion — now also skips SDD installs detected by `SKILL.md` presence, known SDD substrings (`bmad`, `cicadas`, `gsd`, `openspec`) in root-level `.`/`_` dirs, and user-configured `scan_exclude_paths` entries.

## 0.1.0

- Initial release of gavel-ai: provider-agnostic LLM evaluation framework.
- OneShot workflow with `ScenarioProcessorStep`, `PromptInputProcessor`, and `GEval`/`DeepEval` judge adapters.
- Pydantic-AI provider factory supporting Anthropic, OpenAI, Gemini, and Ollama.
- Filesystem-based JSONL artifact storage and Jinja2 HTML/Markdown report generation.
- OpenTelemetry instrumentation for all LLM calls and judge steps.
- CLI commands: `gavel oneshot create`, `run`, `judge`, `report`.
