# Tweaklet: Normalize Judge Score Scale to 0.0-1.0

## Intent

Gavel-ai's persisted/displayed judge score is currently a **1-10 integer**, manufactured by remapping DeepEval's native 0.0-1.0 output (`1 + raw*9`). This contradicts the intended system default of **0.0-1.0 float**, which is currently only realized inside Autotune's internal convergence layer (which itself works by dividing the 1-10 score back down by 10). Standardize on 0.0-1.0 as the one true scale everywhere: persisted records, reports, thresholds, and canon.

## Proposed Change

**Models** (`src/gavel_ai/models/runtime.py`):
- `JudgeResult.score`, `JudgeEvaluation.score`, `JudgedRecord.score`: change `int = Field(..., ge=1, le=10)` → `float = Field(..., ge=0.0, le=1.0)`.

**DeepEval judge** (`src/gavel_ai/judges/deepeval_judge.py`):
- Remove the `_normalize_score()` remap to 1-10; pass DeepEval's native 0.0-1.0 `metric.score` straight through (clamped to [0.0, 1.0]).
- Update the "binary/strict_mode GEval normalizes to 1 or 10" comment (`models/config.py:216`) to "0.0 or 1.0".
- `threshold` handling (lines 223, 287, 320-324) is unaffected — it already operates on DeepEval's native 0-1 scale and is passed straight to the underlying metric.

**External/custom judges** (`src/gavel_ai/core/steps/judge_runner.py`):
- Line ~308-324: clamp raw external scores to `max(0.0, min(1.0, float(raw_score)))` instead of the 1-10 int clamp.

**Autotune** (highest-risk area — two independent normalization paths):
- `src/gavel_ai/core/autotune/scoring.py::normalize_score()`: the `/10.0` branch becomes a pass-through (LLM-judge scores are already 0.0-1.0 natively now); deterministic pass-through unchanged.
- `src/gavel_ai/core/steps/tune_step.py::_compute_avg_score()` (~line 102-113): currently does its own **hardcoded** `(sum(scores)/len(scores)) / 10.0`, independent of `scoring.py`. Must become a plain average with no `/10.0`, or this silently double-normalizes (produces scores 10x too small) once `JudgeResult.score` is native 0.0-1.0. This is the single easiest thing to miss.
- `src/gavel_ai/core/steps/autotune_iteration_step.py` (`_flatten_judge_scores`/`_compute_judge_scores`/`_compute_overall_score`) already routes through `normalize_score()`, so fixing that one function keeps this path correct.

**Reporters** (display only, no schema change needed beyond the model type change):
- `src/gavel_ai/reporters/templates/base.html:207`: remove the `/10` suffix, format as a 0.0-1.0 value (e.g. 2 decimal places) or a percentage — match whatever the oneshot template already does for deterministic scores for visual consistency.
- `src/gavel_ai/reporters/templates/oneshot.html:557`: same formatting pass.
- `src/gavel_ai/judges/judge_executor.py:117`: update the log line from `f"...scored {result.score}/10..."` to reflect the new scale.
- `jinja_reporter.py`/`oneshot_reporter.py` additive aggregation (`avg_score`, `total_score`, `judge_sums`) is scale-agnostic arithmetic — no code change required, but the *meaning* of `total_score` shifts from "out of N×10" to "out of N×1.0"; call this out to a reader in a comment if the code reads oddly with the new scale.

**Docs & canon** (update while touching this, since they hard-declare the old scale):
- `docs/specs/schema-outputs.md` (lines 81, 88, 136, 246) and `docs/specs/schema-configs.md` (108-112): update score-scale prose; also fix the pre-existing factual error that says "DeepEval returns 0-10" (it returns 0.0-1.0 natively — the old `/10.0` was dividing gavel's own remapped 1-10 value, not DeepEval's raw output).
- `.cicadas/canon/slices/src-gavel_ai/invariants.md:6` — formally declares "All judges must output a score on a 1-10 integer scale." Update to 0.0-1.0 as part of the Significance Check / canon update.
- `.cicadas/canon/schema.md` (273, 359, 363-364), `.cicadas/canon/tech-overview.md` (110, 139), `.cicadas/canon/summary.md:60` — same terminology to update.

**Out of scope**: `IterationMetadata.score`, `AutotuneRunSummary` fields, `PerSampleDeterministicResult.raw_score`, `DeterministicRunResult.population_score`, and deterministic classifier/regression judges (already 0/1, pass through unchanged, no scaffolding template changes needed — thresholds in generated configs are already expressed in native 0.0-1.0 terms).

## Tasks
- [x] Update `JudgeResult.score`, `JudgeEvaluation.score`, `JudgedRecord.score` to `float, ge=0.0, le=1.0` in `models/runtime.py` <!-- id: 10 -->
- [x] Remove 1-10 remap in `deepeval_judge.py` (`_normalize_score`), pass native DeepEval score through clamped to [0.0, 1.0]; update `config.py:216` comment <!-- id: 11 -->
- [x] Update external/custom judge score clamp in `judge_runner.py` to [0.0, 1.0] float <!-- id: 12 -->
- [x] Fix `tune_step.py::_compute_avg_score` to drop the hardcoded `/10.0` (avoid double-normalization) <!-- id: 13 -->
- [x] Update `scoring.py::normalize_score()` LLM-judge branch to pass-through (no-op) <!-- id: 14 -->
- [x] Update score display in `base.html`, `oneshot.html`, and the `judge_executor.py` log line <!-- id: 15 -->
- [x] Update all affected unit/integration tests (see explore findings: `test_judge_base.py`, `test_result_storage.py`, `test_judge_executor.py`, `test_deepeval_judge.py`, `test_scoring.py`, `test_autotune_iteration_step.py`, `test_tune_step.py`, `test_external_runner_foundation.py`, `test_oneshot_e2e.py`, `test_external_runner_e2e.py`, `test_autotune_workflow.py`, `test_judge_runner_mixed.py`) <!-- id: 16 -->
- [x] Update `docs/specs/schema-outputs.md` and `docs/specs/schema-configs.md` score-scale sections <!-- id: 17 -->
- [x] Run full test suite (`uv run pytest -m unit` and `-m integration`) and fix regressions <!-- id: 18 -->
- [x] Verify functionality <!-- id: 19 -->
- [x] Significance Check: Does this warrant a Canon update? <!-- id: 20 -->
  - Yes — update `.cicadas/canon/slices/src-gavel_ai/invariants.md`, `canon/schema.md`, `canon/tech-overview.md`, `canon/summary.md` to reflect the 0.0-1.0 scale. Deferred to initiative-completion synthesis on `main` per guardrail #6 (no canon writes on branches).

## Implementation Notes (Reflect)

All tasks completed as scoped. Full test suite green except two pre-existing, unrelated failures (both fail identically on `master` before this change):
- `tests/unit/test_cli.py::test_gavel_version` — hardcoded version string `0.2.0` vs. installed `0.2.2`.
- `tests/unit/test_metadata_performance.py::test_timing_accuracy` — timing-tolerance flake.

Additional touchpoints found and fixed beyond the original draft (via a second Explore pass before implementation):
- A third score model, `JudgeEvaluation.score` (`models/runtime.py`), not just `JudgeResult`/`JudgedRecord`.
- `jinja_reporter.py`'s `variant_scores: Dict[str, List[int]]` type hint corrected to `List[float]`.
- Docstring/comment cleanup in `judges/base.py`, `judges/deepeval_judge.py`, and the packaged skill reference `src/gavel_ai/skill/gavel-skill/references/judges-reference.md` (score-scale table and threshold semantics).
- Test fixture `tests/fixtures/scripts/judge_success.py` (external judge protocol test double) updated to emit `score: 0.8` instead of `score: 8`, since external judges now report natively on 0.0-1.0.

No canon files were touched on this branch (guardrail #6); canon reconciliation happens at initiative completion.
