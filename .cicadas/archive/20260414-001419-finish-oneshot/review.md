## Code Review: initiative/finish-oneshot

**Scope:** Full — Initiative Branch (all three partitions merged)
**Spec files read:** tasks.md, tech-design.md, approach.md
**Diff:** 31 files changed, +3352 −286 lines

---

### ✅ Verified

- All 58 tasks in `tasks.md` marked `[x]` with corresponding implementation in the diff — task completeness confirmed
- `DeterministicMetric` hierarchy correctly separated from `Judge` per ADR-1: no `JudgeResult`, no LLM call, no JudgeExecutor involvement
- `ClassifierMetric.evaluate_sample()`: case-insensitive label match, correct skip-reason strings for all three error conditions
- `RegressionMetric.evaluate_sample()`: unbounded signed error (`prediction - actual`), `match=None` per spec
- `ClassifierMetric.__init__()` raises `ConfigError` when `report_metric="fbeta"` and `beta` absent — spec requirement satisfied
- `JudgeRegistry.register("classifier", ClassifierMetric)` and `"regression"` at module level — correct registration pattern
- `StepPhase.PREPARE` added; `mark_step_complete()` called in `Step.safe_execute()` on success path only — per ADR-4
- `LocalRunContext.__init__()` calls `mark_step_complete(StepPhase.PREPARE)` after `snapshot_run_config()` — correct sequencing
- `.workflow_status` is JSONL append-only; `get_completed_steps()` returns `[]` when file absent — both correct
- `snapshot_run_config()`: prompts copied via `shutil.copytree`, `snapshot_metadata.json` written with `snapshotted_at` and `files` — spec satisfied
- `get_judge_config()` raises `ConfigError` (not `FileNotFoundError`) on missing TOML file
- `ValidatorStep` variant resolution gated on `test_subject_type == "local"` — ADR-6 respected
- Prompt existence check gated on `local` type; unregistered judge type is a warning, not a raise
- Empty scenario list raises `ValidationError` — re-enabled correctly per task 33
- `config_ref` TOML resolution happens in `JudgeRunnerStep` before `JudgeExecutor` receives configs — ADR-3 respected
- `OneShotReporter`: error exclusion uses `(scenario_id, variant_id)` set from `raw_results`; `skipped_counts` tracked per `(variant, judge)` — logic correct
- Score averaging computes mean over non-error samples only — matches spec requirement
- `deterministic_results` field added to `ReportData` with empty-list default — backward compatible
- `--template` flag added to CLI with validation against `VALID_TEMPLATES` — exits non-zero for unknown values
- `generate_all_templates()` dispatches on template type correctly
- All 951 unit tests and 31 integration tests pass

---

### 🔴 Blocking

*(None — Reflect resolved the per_sample → samples field rename and updated tech-design.md.)*

---

### 🔶 Advisory

- **[Module Scope]** `src/gavel_ai/providers/factory.py` — Modified to add Google Vertex AI authentication support (`project`, `location` fields in `provider_auth`). This file is not listed in any of the three partition module scopes (`approach.md` §Partitions). The change is a valid improvement but wasn't planned as part of this initiative. Builder should confirm this is intentional scope expansion, not an accidental bleed-in.

- **[Arch Violation]** `src/gavel_ai/judges/deterministic_metric.py` — OTel spans are absent. `tech-design.md` §OTel Spans states: *"`DeterministicMetric.evaluate_sample()` must emit a span using `self.tracer`. Span name: `"deterministic_judge.evaluate"`. Attributes: `judge.name`, `judge.type`, `scenario.id`, `judge.skipped`."* There is no `tracer` attribute or span instrumentation in the class. The gap was not captured in any task or as an amendment to tasks.md.

- **[Arch Violation]** `src/gavel_ai/core/steps/judge_runner.py:170` — Partitioning uses `JudgeRegistry._registry.get(cfg.type)` (private attribute access). `tech-design.md` ADR-2 shows `isinstance(JudgeRegistry.create(cfg), DeterministicMetric)` as the intended routing pattern. The private access is fragile and bypasses the public registry API.

- **[Arch Violation]** `src/gavel_ai/core/contexts.py:396` — `get_judge_config()` uses `import toml` (third-party library, imported inside the method). `tech-design.md` §Tech Stack explicitly states "TOML parsing: `tomllib` (stdlib, Python 3.11+) — Zero new dependency." `toml` was a pre-existing dependency so there is no new install risk, but it deviates from the stated ADR. The in-method import also violates the project's import convention.

- **[Quality]** `src/gavel_ai/core/contexts.py:591–593, 621–622` — In-method imports: `import shutil`, `import json as _json`, `from datetime import timezone` (in `snapshot_run_config()`), and `import json`, `from datetime import timezone` (in `mark_step_complete()`) — none of these require deferred import to avoid circular dependencies. The `StepPhase` deferred imports at lines 472 and 639 are justified by circular-import avoidance; the `shutil`/`json`/`timezone` ones are not.

- **[Quality]** `src/gavel_ai/core/contexts.py:392–393` — `_judge_config_cache` is initialized lazily via `if not hasattr(self, "_judge_config_cache"):` inside `get_judge_config()`. The existing `_prompt_cache` and `_judge_cache` patterns are initialized in `__init__`. The `hasattr` guard is inconsistent with the established pattern, loses IDE type inference, and silently reinitializes if the attribute is accidentally deleted.

- **[Quality]** `src/gavel_ai/reporters/oneshot_reporter.py:205` — `skipped_counts` is injected directly into the Jinja2 template context dict as `ctx["skipped_counts"] = skipped_counts`, bypassing the `ReportData` Pydantic model. Every other field in the report goes through `ReportData.model_dump()`. This breaks schema visibility and type guarantees for the template layer. Recommended fix: add `skipped_counts: Dict[str, Dict[str, int]]` as a field on `ReportData` or a companion dataclass.

---

### 🐛 Correctness

- **[Advisory]** `src/gavel_ai/judges/deterministic_metric.py:277, 292` — In `RegressionMetric.evaluate_sample()`, when `float(prediction_raw)` raises `TypeError`/`ValueError` (line 277), the skip reason is `"prediction_field not found: {field}"`. When `float(actual_value)` raises (line 292), the reason is `"actual_field not found: {field}"`. In both cases the field was found — the value is non-numeric. The misleading message will confuse users debugging type errors in scenario data. Recommended: `"prediction_field not numeric: {field}"` / `"actual_field not numeric: {field}"`.

---

**Verdict: PASS WITH NOTES**
*Blocking findings: 0 (Reflect resolved the per_sample → samples field rename). Advisory findings: 7. Review advisories before merging. This verdict is advisory — Builder retains merge authority.*
