# Release Notes

## Unreleased

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
