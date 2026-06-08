## Summary

Adds **autotune** — an automated prompt-optimization workflow that iteratively rewrites and re-judges a prompt against a scenario set until it converges (max rounds, target score, minimal improvement, or degradation). Delivered across three sequential partitions, each merged into `initiative/feat-autotune` as it landed (single PR deferred to initiative completion per the recorded lifecycle decision):

- **Partition 1 — Foundations** (`1fd6a37`): `TuningConfig`/`IterationMetadata`/`AutotuneRunSummary` data models, `CompositeStep` base, `IterationEvalContext`/`IterationRunContext`, `TuningAgent`, bundled meta-prompt template.
- **Partition 2 — Engine** (`a01cbe3`): `TuneStep`, `AutotuneIterationStep` (4-criteria convergence: `max_rounds_reached` → `target_score_achieved` → `minimal_improvement` → `performance_degraded`), `AutotuneWorkflow` (with resume support), `AutotuneReporter` + HTML report template.
- **Partition 3 — Surface** (`2b68c39`): `gavel autotune create`/`run` CLI commands, `generate_autotune_templates()` scaffolding, 10 new unit tests, regenerated `cli-reference.md`, and a 7-stage autotune section in the `gavel-skill` documentation (`SKILL.md`, `config-schema.md`).

## Validation

- Full unit + integration suites pass aside from 6 pre-existing, unrelated failures (stale version-string assertion, one flaky timing test, four `test_judge_runner_mixed`/`test_oneshot_e2e` integration failures — all reproduced identically on a clean checkout and documented in `tasks.md` at id-211/305).
- End-to-end smoke test against a real LLM (Anthropic Claude Haiku for both the test subject and the judge): `gavel autotune create` → edited scenarios/config → `gavel autotune run` converged at iteration 1 with score `1.000`; `report.html` rendered correctly with populated Score Progression, Per-Judge Detail, and Best Prompt Version sections.

## Test plan

- [x] `uv run pytest -m unit` — 1119 passed (2 pre-existing failures unrelated to this change)
- [x] `uv run pytest -m integration` — 28 passed (4 pre-existing failures unrelated to this change)
- [x] `gavel autotune create --eval <name>` scaffolds a valid `EvalConfig` (round-trips through Pydantic)
- [x] `gavel autotune run --eval <name>` executes end-to-end against a real LLM and produces a converged run + rendered HTML report
- [x] `gavel --help` / `gavel autotune --help` lists the new command group correctly

🤖 Generated with [Claude Code](https://claude.com/claude-code)
