# Judge Pipeline: DRY Refactor & Multi-Variant Fix

## Summary

The oneshot judge pipeline has three inter-related problems:

1. **Duplicate code paths** — `ReJudge` replicates logic already in `JudgeRunnerStep` (model resolution, judge execution, writing `results_judged.jsonl`). The `judge` CLI command also had to duplicate model resolution after a recent bug fix.
2. **Two formats in flight** — `ProcessorResult` and `OutputRecord` represent the same data. The pipeline converts between them mid-flight, adding complexity to every downstream step.
3. **Multi-variant is silently broken** — `ScenarioProcessorStep` hard-codes `variants[0]`, so any eval with more than one variant silently ignores the rest. `JudgeRunnerStep` zips scenarios and results positionally, which only works for single-variant runs.

The fix addresses all three together: unify on `OutputRecord` as the in-pipeline type, loop variants in the processor step, group by `variant_id` in the judge step, and delete `ReJudge` in favor of reusing the same steps.

---

## Current Architecture

```
ScenarioProcessorStep
  - reads variants[0] only  ← bug
  - runs executor → List[ProcessorResult]
  - spools OutputRecord to results_raw.jsonl (via ResultsExporter)
  - stores List[ProcessorResult] in context.processor_results

JudgeRunnerStep
  - zip(scenarios, processor_results)  ← positional, single-variant only
  - resolves model keys
  - runs JudgeExecutor.execute_batch()
  - stores List[EvaluationResult dicts] in context.evaluation_results

ReportRunnerStep
  - calls ResultsExporter.export_judged_results(scenarios, processor_results, evaluation_results)
  - writes manifest.json + report.html

--- separate path for `gavel oneshot judge` ---

judge command
  - resolves model keys  ← duplicated from JudgeRunnerStep
  - creates ReJudge(results_raw.jsonl, judge_configs)
  - ReJudge.rejudge_all()
    - loads OutputRecord from file (new, after recent fix)
    - calls JudgeExecutor.execute() in a loop
    - writes results_judged.jsonl inline
  - calls _generate_report()
```

---

## Proposed Architecture

```
ScenarioProcessorStep
  - loops ALL variants
  - for each variant: runs executor → List[ProcessorResult]
  - converts ProcessorResult → OutputRecord immediately (has all context)
  - writes OutputRecord to results_raw.jsonl as it arrives (streaming, unchanged)
  - stores List[OutputRecord] in context.processor_results  ← type change

JudgeRunnerStep
  - receives List[OutputRecord]  ← no zip, scenario_id is on the record
  - groups records by variant_id
  - for each group: looks up Scenario by scenario_id, runs judges
  - resolves model keys (unchanged)
  - stores results in context.evaluation_results

ReportRunnerStep
  - receives List[OutputRecord] + evaluation_results
  - writes results_judged.jsonl, manifest.json, report.html
  - (simplified — no more parallel scenarios/processor_results args)

--- unified path for `gavel oneshot judge` ---

judge command
  - loads List[OutputRecord] from results_raw.jsonl via run_ctx.results_raw.read()
  - sets context.processor_results = records
  - runs JudgeRunnerStep.execute(context)  ← same code path as normal run
  - runs ReportRunnerStep.execute(context)  ← same code path as normal run

ReJudge  ← deleted entirely
```

---

## Detailed Changes

### 1. `context.processor_results` type change

**File:** `src/gavel_ai/core/contexts.py`

Change the type annotation on `RunContext.processor_results` from `Optional[List[ProcessorResult]]` to `Optional[List[OutputRecord]]`. Update any `TYPE_CHECKING` imports accordingly.

---

### 2. `ScenarioProcessorStep` — multi-variant loop + OutputRecord output

**File:** `src/gavel_ai/core/steps/scenario_processor.py`

**Current behaviour:** Reads `variants[0]`, runs the executor once, stores `List[ProcessorResult]`.

**New behaviour:**
- Loop over all entries in `eval_config.variants`.
- For each variant, resolve model definition, instantiate processor, run executor.
- Convert each `ProcessorResult` → `OutputRecord` immediately inside the step (all required fields — `test_subject`, `variant_id`, `scenario_id`, `timing_ms`, `tokens_prompt`, `tokens_completion` — are available at this point).
- Stream each `OutputRecord` to `results_raw.jsonl` as it arrives (existing `_spool_result` pattern, but now writes the `OutputRecord` directly instead of going through `ResultsExporter.append_raw_result`).
- Accumulate all `OutputRecord` objects across all variants into one list.
- Set `context.processor_results = all_output_records`.
- Set `context.test_subject` to the first test subject name (kept for logging/reporting context; with multi-variant it no longer uniquely identifies the run).
- Set `context.model_variant` to a comma-joined summary or drop it (it's only used for display).

**ProcessorResult → OutputRecord conversion:**
```python
OutputRecord(
    test_subject=test_subject,
    variant_id=model_variant,
    scenario_id=input_item.id,
    processor_output=str(proc_result.output),
    timing_ms=int(proc_result.metadata.get("latency_ms", 0)),
    tokens_prompt=int(proc_result.metadata.get("tokens", {}).get("prompt", 0)),
    tokens_completion=int(proc_result.metadata.get("tokens", {}).get("completion", 0)),
    error=proc_result.error,
    metadata=proc_result.metadata,
    timestamp=datetime.now(timezone.utc).isoformat(),
)
```

---

### 3. `JudgeRunnerStep` — group by variant_id, use scenario_id lookup

**File:** `src/gavel_ai/core/steps/judge_runner.py`

**Current behaviour:** `zip(scenarios, processor_results, strict=True)` — positional, single-variant.

**New behaviour:**
- Receive `List[OutputRecord]` from context.
- Build a scenario lookup dict: `scenario_map = {s.id: s for s in scenarios}`.
- Group records by `variant_id`: `groups: Dict[str, List[OutputRecord]]`.
- For each variant group:
  - Build `evaluations_batch = [(scenario_map[r.scenario_id], r.processor_output, r.test_subject) for r in group]`
  - Run `judge_executor.execute_batch(evaluations_batch, subject_id=r.test_subject, ...)`.
- Collect all evaluation results across variants.
- Store in `context.evaluation_results`.

Model resolution logic is unchanged — it still resolves before the loop.

---

### 4. `ReportRunnerStep` — accept OutputRecord list

**File:** `src/gavel_ai/core/steps/report_runner.py`

**Current behaviour:** Calls `ResultsExporter.export_judged_results(scenarios, processor_results, judge_evaluations, ...)` which does its own conversion.

**New behaviour:**
- Receive `List[OutputRecord]` from `context.processor_results`.
- `results_raw.jsonl` is already complete (streamed by the processor step) — no change here.
- Write `results_judged.jsonl` directly from `OutputRecord` list + `evaluation_results` (already in `context.evaluation_results`).
- The write logic joins on `scenario_id`: for each `OutputRecord`, find its `EvaluationResult` and embed the `judges` array.
- `manifest.json` generation is unchanged.

---

### 5. `ResultsExporter` — simplify or delete

**File:** `src/gavel_ai/storage/results_exporter.py`

After the changes above, `ResultsExporter` is responsible only for:
- `append_raw_result()` — superseded by inline `OutputRecord` write in the processor step.
- `export_raw_results()` — no longer called (streaming replaces it).
- `export_judged_results()` — superseded by inline write in `ReportRunnerStep`.
- `compute_config_hash()` — still needed, keep as a standalone function or move to a utils module.

**Decision:** Delete `ResultsExporter` class. Move `compute_config_hash` to `src/gavel_ai/storage/utils.py` or inline it in `ReportRunnerStep`.

---

### 6. `judge` CLI command — reuse pipeline steps

**File:** `src/gavel_ai/cli/commands/oneshot.py`

**Current behaviour:** Creates `ReJudge`, runs `rejudge_all()`, calls `_generate_report()`.

**New behaviour:**
```python
# Load existing processor outputs
records = list(run_ctx.results_raw.read())  # → List[OutputRecord]
if not records:
    raise ResourceNotFoundError(...)

# Build a minimal context with what the steps need
context = LocalRunContext(eval_ctx=eval_ctx, base_dir=..., run_id=run_id, snapshot=False)
context.processor_results = records

# Run the standard pipeline steps (model resolution lives in JudgeRunnerStep)
judge_step = JudgeRunnerStep(app_logger)
await judge_step.execute(context)

report_step = ReportRunnerStep(app_logger)
await report_step.execute(context)
```

Remove `--judges` filter option or implement it by pre-filtering `eval_config.test_subjects[].judges` before the step runs (same as before, but now it's the step doing the work).

Remove all model resolution code added to the command in the recent bug fix — it moves back into `JudgeRunnerStep` where it belongs.

---

### 7. Delete `ReJudge`

**Files to delete:**
- `src/gavel_ai/judges/rejudge.py`
- `tests/unit/test_rejudge.py`

Remove `ReJudge` from `src/gavel_ai/judges/__init__.py`.

---

## Data Model Notes

`OutputRecord` gains one field that was previously absent: `metadata: Dict[str, Any]` (already in the Pydantic model, but not consistently populated by `ResultsExporter`). The new processor step populates it from `ProcessorResult.metadata`. Downstream steps and the reporter should treat it as optional/passthrough.

`ProcessorResult` is not deleted — it remains the return type of the low-level processors (`PromptInputProcessor`, `ClosedBoxInputProcessor`). The conversion to `OutputRecord` happens exclusively in `ScenarioProcessorStep`.

---

## Files Changed

| File | Change |
|------|--------|
| `src/gavel_ai/core/contexts.py` | `processor_results` type: `List[ProcessorResult]` → `List[OutputRecord]` |
| `src/gavel_ai/core/steps/scenario_processor.py` | Multi-variant loop; output `List[OutputRecord]` |
| `src/gavel_ai/core/steps/judge_runner.py` | Group by `variant_id`; scenario lookup by id |
| `src/gavel_ai/core/steps/report_runner.py` | Accept `List[OutputRecord]`; inline judged write |
| `src/gavel_ai/cli/commands/oneshot.py` | `judge` command: load records, run steps directly |
| `src/gavel_ai/storage/results_exporter.py` | Delete class; extract `compute_config_hash` |
| `src/gavel_ai/judges/rejudge.py` | **Delete** |
| `tests/unit/test_rejudge.py` | **Delete** |
| `tests/unit/test_steps.py` | Update mocks for new `processor_results` type |
| `tests/unit/steps/test_report_runner.py` | Update for new input types |

---

## What Does Not Change

- `results_raw.jsonl` file format — `OutputRecord` schema is unchanged.
- `results_judged.jsonl` file format — combined format with embedded `judges[]` array, unchanged.
- `manifest.json` format — unchanged.
- Low-level processors (`PromptInputProcessor`, `ClosedBoxInputProcessor`) — return `ProcessorResult`, unchanged.
- `JudgeExecutor` — unchanged.
- `DeepEvalJudge` and other judge implementations — unchanged.
- The conversational pipeline — separate code path, out of scope.
