# Release Notes

## Unreleased

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
