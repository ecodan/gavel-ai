---
summary: "Build on `gavel oneshot create --type external`: scaffold both script and HTTP SUT variants with distinct names (script active as test_subjects[0], http inert as [1]), fix --type help text, and add `gavel oneshot analyze --run <id>` perf-metrics command. No new closed-box command group — external targets stay config-driven inside oneshot."
phase: "tasks"
when_to_load:
  - "When implementing or reviewing the tweak/external-sut-scaffold-analyze branch"
depends_on:
  - "docs/specs/schema-external-runner.md"
  - "docs/specs/schema-outputs.md"
modules:
  - "src/gavel_ai/cli/commands/oneshot.py"
  - "src/gavel_ai/cli/scaffolding.py"
  - "src/gavel_ai/scaffolds/_materialize.py"
index:
  tasks: "## Tasks"
next_section: "## Tasks"
---

# Tweaklet: external-sut-scaffold-analyze

## Intent

Close the "Closed-box CLI" punch-list item (item 4) without adding a `closed-box` command group. The runtime already supports external systems under test end-to-end (`ScenarioProcessorStep` dispatches on `test_subject_type: "external"` + `protocol: "http" | "script"`; `oneshot run/judge/report` work unchanged). What's missing is discoverability and ergonomics:

1. `gavel oneshot create --type external` exists but is undocumented in help text, defaults to HTTP only, and scaffolds a single variant.
2. There is no perf-metrics command (`analyze`) over `results_raw.jsonl`.

**Decision recorded**: closed-box is a *target*, not a *workflow* — it is configured via the test subject in `eval_config.json`, and lives inside the `oneshot` command group. A separate `gavel closed-box` group (the reference app's shape) was considered and rejected.

## Proposed Change

### 1. Dual-variant external scaffold (`cli/scaffolding.py`) — implemented as planned, plus one addition

`_generate_external_templates(eval_root, eval_name, ...)` generates `eval_config.json` with **two** entries in `test_subjects`:

- `[0]` — `system_id: "sut-script"`, `protocol: "script"`, `config.command: [sys.executable, <absolute path to sut_script_scaffold.py>]` — **active**, `judges` populated.
- `[1]` — `system_id: "sut-http"`, `protocol: "http"`, `config.endpoint: "http://localhost:8080/evaluate"` — inert placeholder, **`judges: []`**.

**Divergence from plan**: the command path uses an absolute path (`sys.executable` + resolved script path), not a relative `["python", "scripts/..."]` list as originally sketched. `ScriptInputProcessor` launches the subprocess with a fresh per-scenario temp dir as `cwd`, so a relative path would never resolve — discovered via the end-to-end test (see below).

**Divergence from plan**: the inert subject is scaffolded with `judges: []`, not a copy of the real judges list. `JudgeRunnerStep` pools `judges` across *every* `test_subjects` entry, not just index 0 — giving both subjects the same judges would silently double-run (and double-bill) every judge. Documented in the generated config's `description` and in `schema-configs.md`.

`generate_all_templates` (external branch) materializes both scaffolds via `_materialize(..., name="sut_script")` → `sut_script_scaffold.py` and `_materialize(..., name="sut_http")` → `sut_http_scaffold.py`. The script scaffold template gained the commented "call your remote API from here" section in `handle()`.

### 2. Help-text fix (`cli/commands/oneshot.py`) — done as planned

`VALID_TYPES = ("local", "in-situ", "external")`; `--type` help documents all three and unknown values raise `ValidationError` cleanly (previously unvalidated pass-through).

### 3. `gavel oneshot analyze` (`cli/commands/oneshot.py`) — implemented, metrics source differs from plan

New command `gavel oneshot analyze --run <run_id> [--eval <name>] [--eval-root ...]`, following the `judge` command's pattern (`_get_eval_dir`, `LocalRunContext`, `_EvalRootArg`).

**Divergence from plan**: metrics read directly from `OutputRecord`'s top-level fields (`timing_ms`, `tokens_prompt`, `tokens_completion`, `error`, `timestamp`), not `metadata.total_latency_ms` — those fields are first-class on the model, not nested in metadata. There is also no persisted WARNING/ERROR tier on `OutputRecord` (only `error: Optional[str]`), so the table reports success/error only, not a three-way split.

Rich table: scenario count, success/error counts + error rate, latency avg/p50/p95, throughput (records/sec across the timestamp span), token totals. Pure function `compute_run_metrics()` lives in the new `core/run_metrics.py`, independently unit-tested.

### 4. Bug fix discovered via the end-to-end test (not in original plan)

The end-to-end script-execution test surfaced two pre-existing correctness bugs in `ScenarioProcessorStep` (`core/steps/scenario_processor.py`), affecting **all** external SUT runs regardless of this tweak:

1. The outbound payload for both `http` and `script` branches only ever included `{"scenario_id", "input", "metadata"}` — never `scenario_input` or `rendered_prompt`, both **required** by `ExternalTaskRequest`, which the scaffold SDK's `_BaseSystemUnderTest._parse_and_validate` validates against. Every external SUT invocation failed schema validation at the SUT boundary. Fixed by building `scenario_input`, `rendered_prompt` (falls back to `str(scenario.input)`), and `custom_config` (subject's `config` dict, passthrough) in both branches.
2. (See judge-pooling note above — same investigation surfaced it.)

Builder approved fixing both in this tweak rather than escalating to a separate initiative, given the contained size and direct relevance to "closed-box actually runs out of the box."

### 5. Tests (real tmp dirs, minimal mocking) — done, plus regression coverage for the bug fix

- Unit: dual-variant scaffold generation (`tests/integration/test_scaffold_materialize.py`) — both files exist, `ast.parse`, config has 2 subjects in the right order/protocol/names, active has judges, inactive has `judges: []`.
- Unit: `--type` validation (`tests/unit/test_oneshot_create.py`).
- Unit: analyze metrics math (`tests/unit/core/test_run_metrics.py`) — counts, percentiles, throughput, malformed-timestamp tolerance, empty-set error.
- Integration: `create --type external` → `run` end-to-end against the real `sut_script_scaffold.py` subprocess (`tests/integration/test_oneshot_external_script_e2e.py`) — this is what surfaced the payload bug.
- Integration: `analyze` CLI (`tests/integration/test_oneshot_analyze.py`).

### 6. Docs

- `docs/cli-reference/` does not exist as a populated directory in this repo (checked — empty); documented instead in `docs/specs/schema-configs.md` (`test_subject_type: "external"`, judge-pooling note) and `docs/specs/schema-external-runner.md` (new "CLI Scaffolding" section).
- Punch list item 4 marked Done with the "no separate command group" decision and a summary of the discovered/fixed bugs.

**Out of scope** (deferred to a future initiative, confirmed still deferred): first-class `turns` schema in `ExternalResponseEnvelope`, long-running/agentic timeout ergonomics, streaming/progress.

## Tasks
- [x] Dual-variant scaffold: extend `_generate_external_templates` + `generate_all_templates` to emit both subjects and both materialized scaffolds; add API-call comment block to script template <!-- id: 10 -->
- [x] Fix `--type` help text and add value validation in `oneshot create` <!-- id: 11 -->
- [x] Add `gavel oneshot analyze` command with pure metrics function <!-- id: 12 -->
- [x] Fix `ScenarioProcessorStep` external payload to satisfy `ExternalTaskRequest` (scenario_input/rendered_prompt/custom_config) — discovered via e2e test <!-- id: 17 -->
- [x] Tests: scaffold generation, type validation, analyze metrics, end-to-end script run <!-- id: 13 -->
- [x] Docs: schema-configs.md + schema-external-runner.md + punch-list update (no cli-reference dir exists) <!-- id: 14 -->
- [x] Verify functionality (`uv run pytest -m unit && uv run pytest -m integration`) <!-- id: 15 -->
- [x] Significance Check: Does this warrant a Canon update? <!-- id: 16 --> — Yes: updated `tech-overview.md` (CLI command list, `--type external` dual-scaffold, judge-pooling caveat, external payload construction) and `summary.md` (analyze command, closed-box conventions).
