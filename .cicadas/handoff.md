---
boundary: "initiative-complete"
initiative: "external-runner"
---

# Handoff: external-runner — All Partitions Merged, PR Open

## Just completed

All seven partitions merged into `initiative/external-runner` (now at `a1a0ebc`):

- **P1 feat/external-runner-foundation** — config/runtime models (`TestSubjectType`, `ExternalOutcome`), `classify_external_outcome`, `adapter` seam (ADR-10), `config-schema.md` correction (ADR-9)
- **P2 feat/external-http-rename** — `ExternalHttpProcessor`, HTTP transport, scenario routing, `trace_id` wiring
- **P3 feat/external-script-processor** — `ScriptInputProcessor`, asyncio subprocess, tmp-dir lifecycle, path-confinement fix, classify wiring
- **P5 feat/external-runner-schemas** — `ExternalTaskRequest` + `ExternalJudgeRequest` Pydantic models, JSON schema files, `schema-external-runner.md`, cross-links
- **P4 feat/external-judge-delegation** — `JudgeConfig.protocol`/`system_id`, `_execute_external_judge()` in `judge_runner.py`, judge fixture scripts, 27 unit + 5 integration tests
- **P6 feat/external-runner-scaffolds** — `gavel_ai.scaffolds` package (`_BaseSystemUnderTest`, `RemoteSystemUnderTest`, `ScriptSystemUnderTest`, `_materialize.py`), scaffold templates, `gavel init` hook, 19 unit + 6 integration tests
- **P7 feat/external-runner-skill-flows** — SKILL.md §2/§10 external setup + two-tier debug guidance, cli-reference.md, walkthrough transcript

**PR**: https://github.com/ecodan/gavel-ai/pull/7 (`initiative/external-runner` → `master`)

## Approved/authoritative state

- `.cicadas/active/external-runner/tasks.md` — all 71 tasks `[x]`
- `initiative/external-runner` at `a1a0ebc` — authoritative, pushed
- PR #7 open, awaiting merge approval

## Next action (after PR merge)

1. **Canon synthesis** — run `cicadas synthesize external-runner --initiative` on `master` after merge to reverse-engineer updated canon docs from the merged code
2. **Archive** — run `cicadas archive external-runner --type initiative` to move active specs to `.cicadas/archive/` and deregister from registry
3. Commit and push the archive move + registry deletion

## Reload list (for post-merge synthesis)

- `src/gavel_ai/models/config.py` — `JudgeConfig.protocol`, `TestSubject` external fields
- `src/gavel_ai/models/runtime.py` — `ExternalTaskRequest`, `ExternalJudgeRequest`, `ExternalResponseEnvelope`, `ExternalIssue`
- `src/gavel_ai/core/steps/judge_runner.py` — `_execute_external_judge`, routing logic
- `src/gavel_ai/processors/external_http_processor.py`
- `src/gavel_ai/processors/script_processor.py`
- `src/gavel_ai/scaffolds/` — full new package
- `docs/specs/schema-external-runner.md`
- `src/gavel_ai/skill/gavel-skill/SKILL.md` — §2 and §10 additions

## Carry forward

**Code Review advisories (non-blocking, carry to post-merge cleanup):**

- `gavel_ai.scaffolds` isolation: `models/utils.py:12` imports `ConfigError` from `gavel_ai.core.exceptions`, which transitively leaks `gavel_ai.core.*` into scaffold imports. Pre-existing coupling; fix by moving `ConfigError` to `models/exceptions.py` or a shared `gavel_ai.exceptions` module.
- `_materialize.py` protocol in `cli/scaffolding.py` hardcodes `protocol="http"` — script scaffold unreachable via `gavel init`. MVP acceptable; wire `protocol="script"` path for full coverage.
- Isolation test in `tests/unit/scaffolds/test_base_scaffold.py::test_import_scaffold_does_not_pull_in_core` is structurally weak (passes because core is pre-loaded by pytest); tighten with subprocess isolation if the advisory above is fixed.

**Pre-existing test failures (unchanged vs. master):**
- `test_conversation_timeout_error.py::test_max_duration_enforcement` — timing-dependent, intermittent
- `test_judge_runner_mixed.py` (3 tests), `test_oneshot_e2e.py`, `test_oneshot_run_wiring.py::test_eval_context_missing_scenarios`, `test_results_export.py::test_conversational_export_integration`
- `test_variant_execution.py::test_multi_variant_execution_flow`
- `test_judge_executor.py` (many) — contaminated by above integration test failures when full suite runs; passes in isolation

**Version**: `pyproject.toml` is `0.2.0` (bumped by P5 agent when adding `jsonschema` dep)
