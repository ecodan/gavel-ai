---
summary: "Type-safe pipeline refactor: add typed step-result attrs to LocalRunContext (List[OutputRecord] for processor_results), loop all variants in ScenarioProcessorStep (convert inline, stream to JSONL), group by variant_id in JudgeRunnerStep (execute_batch per variant group), join on (scenario_id, variant_id) in ReportRunnerStep, delete ReJudge + ResultsExporter, move compute_config_hash to storage/utils.py, reuse pipeline steps in judge CLI. No new dependencies, no schema changes."
phase: "tech"
when_to_load:
  - "When implementing any step in this initiative — defines all interfaces, patterns, and sequences."
  - "When checking whether a change conforms to the agreed design."
depends_on:
  - "prd.md"
  - "ux.md"
modules:
  - "core/contexts.py"
  - "core/steps/scenario_processor.py"
  - "core/steps/judge_runner.py"
  - "core/steps/report_runner.py"
  - "cli/commands/oneshot.py"
  - "storage/results_exporter.py"
  - "judges/rejudge.py"
  - "storage/utils.py"
index:
  overview: "## Overview & Context"
  stack: "## Tech Stack & Dependencies"
  structure: "## Project / Module Structure"
  adrs: "## Architecture Decisions (ADRs)"
  data_models: "## Data Models"
  interfaces: "## API & Interface Design"
  conventions: "## Implementation Patterns & Conventions"
  security_performance: "## Security & Performance"
  implementation_sequence: "## Implementation Sequence"
next_section: null
---

# Tech Design: judge-dry-fix

## Progress

- [x] Overview & Context
- [x] Tech Stack & Dependencies
- [x] Project / Module Structure
- [x] Architecture Decisions (ADRs)
- [x] Data Models
- [x] API & Interface Design
- [x] Implementation Patterns & Conventions
- [x] Security & Performance
- [x] Implementation Sequence

---

## Overview & Context

This initiative is a targeted brownfield refactor of the OneShot judge pipeline. The current pipeline mixes two in-flight data types (`ProcessorResult` and `OutputRecord`), duplicates judge execution logic in `ReJudge`, and hard-codes `variants[0]`, causing silent data loss on multi-variant runs.

The design unifies on `OutputRecord` as the single in-pipeline type from the moment `ScenarioProcessorStep` produces results. `ProcessorResult` remains the output of the low-level processor functions — the conversion happens once, immediately, inside `ScenarioProcessorStep`. From that point, every downstream step deals exclusively with `OutputRecord`. `ReJudge` is deleted; `judge` CLI reuses `JudgeRunnerStep` and `ReportRunnerStep` directly. `ResultsExporter` is deleted; each step writes its own artifacts inline.

### Cross-Cutting Concerns

1. **Context attribute type safety** — `processor_results`, `evaluation_results`, `test_subject`, and `model_variant` are currently set as dynamic attributes on `LocalRunContext`. They must be declared as explicit typed instance attributes to catch type errors at development time and to make the contract legible to downstream steps.

2. **`results_raw.jsonl` immutability** — The file is append-only and must never be rewritten. `ScenarioProcessorStep` continues streaming records directly; no other step touches it.

3. **Join correctness** — `ReportRunnerStep` must join `OutputRecord` with `EvaluationResult` on `(scenario_id, variant_id)`. Positional alignment (the current `zip`) is not correct for multi-variant runs and must be replaced.

4. **Conversational path isolation** — `ConversationalProcessorStep` also sets `context.test_subject` and `context.model_variant`. Those assignments must remain valid after we add typed attrs to `LocalRunContext`. No other changes to the conversational path.

### Brownfield Notes

- **Do not change** `results_raw.jsonl` or `results_judged.jsonl` on-disk schemas.
- **Do not change** `ProcessorResult` — it remains the return type of low-level processors.
- **Do not change** `JudgeExecutor`, `DeepEvalJudge`, or any other judge implementation.
- **Do not change** the conversational pipeline.
- `metadata` field on `OutputRecord` already exists (`Dict[str, Any]`, `default_factory=dict`) — populate it from `ProcessorResult.metadata` in the conversion.

---

## Tech Stack & Dependencies

| Category | Selection | Rationale |
|----------|-----------|-----------|
| Language/Runtime | Python 3.10+ | Unchanged |
| Storage | `jsonlines` | Unchanged — inline writes replace `ResultsExporter` |
| Testing | `pytest`, `unittest.mock` | Unchanged |

**New dependencies introduced:** None.

**Dependencies implicitly removed:** `ResultsExporter` is the only consumer of `jsonlines` in the storage layer. After deletion, `jsonlines` is still used by `RecordDataSource` — no package removal needed.

---

## Project / Module Structure

Files this initiative changes:

```
src/gavel_ai/
├── core/
│   ├── contexts.py                  # [MODIFIED] Add typed step-result attrs to LocalRunContext
│   └── steps/
│       ├── scenario_processor.py    # [MODIFIED] Multi-variant loop; OutputRecord output
│       ├── judge_runner.py          # [MODIFIED] Group by variant_id; scenario_id lookup
│       └── report_runner.py        # [MODIFIED] Accept List[OutputRecord]; inline judged write
├── cli/
│   └── commands/
│       └── oneshot.py              # [MODIFIED] judge command: load records, run steps, no ReJudge
├── judges/
│   └── rejudge.py                  # [DELETED]
└── storage/
    ├── results_exporter.py         # [DELETED]
    └── utils.py                    # [NEW] compute_config_hash standalone function

tests/unit/
├── steps/
│   └── test_report_runner.py       # [MODIFIED] Update for OutputRecord input
├── test_rejudge.py                 # [DELETED]
├── test_steps.py                   # [MODIFIED] Update processor_results mocks
└── test_deepeval_judge.py          # [unchanged — judge impls not touched]
```

**Key structural decisions:**
- `storage/utils.py` is a new thin module — only `compute_config_hash` goes there. No other utilities are pre-emptively added.
- `ResultsExporter` is deleted entirely, not left as a stub. The `export_judged_results` logic moves inline into `ReportRunnerStep`; `append_raw_result` logic moves inline into `ScenarioProcessorStep`.

---

## Architecture Decisions (ADRs)

### ADR-1: Add Typed Step-Result Attributes to `LocalRunContext`

**Decision:** Declare `processor_results`, `evaluation_results`, `test_subject`, and `model_variant` as explicit typed instance attributes initialized to `None` in `LocalRunContext.__init__`, rather than relying on dynamic attribute assignment.

```python
# In LocalRunContext.__init__, after _init_artifacts():
self.processor_results: Optional[List[OutputRecord]] = None
self.evaluation_results: Optional[List[Dict[str, Any]]] = None
self.test_subject: Optional[str] = None
self.model_variant: Optional[str] = None
```

**Rationale:** The ABC (`RunContext`) does not and should not define these — they are step-communication slots, not storage abstractions. But `LocalRunContext` is the concrete type that all steps receive; declaring them there gives type checkers and readers a clear contract. The conversational processor also sets `test_subject` and `model_variant`, so the attributes are shared across workflows.

**Affects:** `contexts.py`, every step that reads/writes these attrs, tests.

---

### ADR-2: Convert `ProcessorResult → OutputRecord` Immediately in `ScenarioProcessorStep`

**Decision:** The conversion from `ProcessorResult` to `OutputRecord` happens inside `ScenarioProcessorStep`, immediately after each result arrives from the executor. No conversion outside this step.

```python
def _make_output_record(
    proc_result: ProcessorResult,
    input_item: Input,
    test_subject: str,
    variant_id: str,
) -> OutputRecord:
    metadata = proc_result.metadata or {}
    return OutputRecord(
        test_subject=test_subject,
        variant_id=variant_id,
        scenario_id=input_item.id,
        processor_output=str(proc_result.output),
        timing_ms=int(metadata.get("latency_ms", 0)),
        tokens_prompt=int((metadata.get("tokens") or {}).get("prompt", 0)),
        tokens_completion=int((metadata.get("tokens") or {}).get("completion", 0)),
        error=proc_result.error,
        metadata=metadata,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
```

**Rationale:** `ScenarioProcessorStep` is the only place that has all three required inputs simultaneously: `ProcessorResult`, `Input` (which carries `scenario_id`), and the variant context (`test_subject`, `variant_id`). Converting here eliminates the need for `ResultsExporter.append_raw_result` and makes the pipeline type-uniform downstream.

**Affects:** `scenario_processor.py`, `results_exporter.py` (deleted), tests.

---

### ADR-3: Multi-Variant Outer Loop in `ScenarioProcessorStep`

**Decision:** Loop over `eval_config.variants` in the outer loop. For each variant: resolve model, instantiate processor, run the executor, convert results to `OutputRecord`, stream each record to `results_raw.jsonl`. Accumulate all `OutputRecord` objects into a single flat list and set `context.processor_results`.

```python
all_records: List[OutputRecord] = []

for variant in eval_config.variants:
    # resolve model, instantiate processor ...
    
    def _spool_result(input_item: Input, result: ProcessorResult) -> None:
        record = _make_output_record(result, input_item, test_subject, model_variant)
        context.run_ctx.results_raw.append(record)  # stream to disk
        all_records.append(record)
    
    await executor.execute(inputs, on_result=_spool_result)

context.processor_results = all_records
context.test_subject = test_subject  # first variant's test subject (display only)
context.model_variant = ", ".join(eval_config.variants)  # summary string for display
```

**Rationale:** The flat list with `variant_id` on each record makes variant identity self-describing. Downstream steps group by `variant_id` rather than receiving separate per-variant lists. This also simplifies the `judge` CLI path (which loads from JSONL — already a flat list).

**Streaming via `RecordDataSource`**: The `LocalRunContext` exposes `results_raw` as a `RecordDataSource`. Use `context.results_raw.append(record)` — not direct `jsonlines` file writes. The storage abstraction must be used so the code remains correct when the backend is not a local filesystem.

**Affects:** `scenario_processor.py`, `results_exporter.py` (deleted), tests.

---

### ADR-4: Group by `variant_id` in `JudgeRunnerStep`; `execute_batch` per Variant Group

**Decision:** Replace `zip(scenarios, processor_results, strict=True)` with:
1. Build `scenario_map = {s.id: s for s in scenarios}`.
2. Group records by `variant_id`: `groups = defaultdict(list); [groups[r.variant_id].append(r) for r in processor_results]`.
3. For each variant group, build a batch of `(scenario, processor_output, variant_id)` tuples and call `judge_executor.execute_batch()`.
4. Collect all `EvaluationResult` objects from all groups into one flat list.
5. Convert to dicts: `context.evaluation_results = [r.model_dump() for r in all_results]`.

```python
scenario_map = {s.id: s for s in scenarios}
groups: Dict[str, List[OutputRecord]] = defaultdict(list)
for r in processor_results:
    groups[r.variant_id].append(r)

all_results: List[EvaluationResult] = []
for variant_id, group in groups.items():
    batch = [(scenario_map[r.scenario_id], r.processor_output, r.variant_id) for r in group]
    results = await judge_executor.execute_batch(
        evaluations=batch,
        subject_id=test_subject,
        test_subject=test_subject,
    )
    all_results.extend(results)

context.evaluation_results = [r.model_dump() for r in all_results]
```

**Rationale:** `EvaluationResult` already carries `scenario_id` and `variant_id`, so the flat list is self-describing. No positional alignment required. Calling `execute_batch` once per variant group (rather than once for all records) preserves the existing batch semantics and progress reporting.

**Affects:** `judge_runner.py`, tests.

---

### ADR-5: Join on `(scenario_id, variant_id)` in `ReportRunnerStep`

**Decision:** Build an evaluation lookup dict from `context.evaluation_results`:
```python
eval_by_key: Dict[tuple, Dict] = {
    (e["scenario_id"], e["variant_id"]): e
    for e in evaluation_results
}
```
Then write `results_judged.jsonl` by iterating `context.processor_results` and looking up each record's judges:
```python
for record in processor_results:
    eval_entry = eval_by_key.get((record.scenario_id, record.variant_id), {})
    entry = {
        **record.model_dump(exclude={"metadata"}),
        "judges": eval_entry.get("judges", []),
    }
    run_context.results_judged.append(entry)
```

**Rationale:** `OutputRecord.model_dump()` produces the same field set as the current `results_judged.jsonl` schema (it carries `test_subject`, `variant_id`, `scenario_id`, `processor_output`, `timing_ms`, `tokens_prompt`, `tokens_completion`, `error`, `timestamp`). Adding `judges` produces the complete judged record. Schema compatibility is preserved.

**`metadata` excluded from `results_judged.jsonl`**: `metadata` is run-level context already accessible from the run directory (`run_metadata.json`, `.config/`). Writing it per-row would be redundant. Use `record.model_dump(exclude={"metadata"})` when building each judged entry.

**Affects:** `report_runner.py`, tests.

---

### ADR-6: Delete `ReJudge`; Reuse Steps in `judge` CLI

**Decision:** The `judge` CLI command is rewritten to:
1. Load `List[OutputRecord]` from `results_raw.jsonl` via `list(run_ctx.results_raw.read())`.
2. Set `context.processor_results = records`.
3. Run `await JudgeRunnerStep(app_logger).execute(context)`.
4. Run `await ReportRunnerStep(app_logger).execute(context)`.

Model resolution is removed from the CLI command entirely — it belongs in `JudgeRunnerStep` and is already there.

```python
records: List[OutputRecord] = list(run_ctx.results_raw.read())
if not records:
    raise ResourceNotFoundError(f"No results found for run '{run_id}'")

context.processor_results = records
await JudgeRunnerStep(app_logger).execute(context)
await ReportRunnerStep(app_logger).execute(context)
```

**`--judges` filter removed**: Judge selection is controlled by `eval_config.test_subjects[].judges` — users edit `eval_config.json` to control which judges run. The CLI option is removed.

**Rationale:** A single code path means a single place to fix bugs, add features, and write tests. `JudgeRunnerStep` already correctly resolves model keys — duplicating that logic in the CLI was the original bug.

**Affects:** `cli/commands/oneshot.py`, `judges/rejudge.py` (deleted), `judges/__init__.py`, tests.

---

### ADR-7: Delete `ResultsExporter`; `compute_config_hash` → `storage/utils.py`

**Decision:** Delete the `ResultsExporter` class entirely. Move `compute_config_hash` as a standalone function to `src/gavel_ai/storage/utils.py`. Update `ReportRunnerStep` to import and call it from there.

**Rationale:** `ResultsExporter` was a container for three concerns: streaming raw results (now inline in `ScenarioProcessorStep`), bulk judged results export (now inline in `ReportRunnerStep`), and config hashing (pure utility). Deleting it removes the class and leaves `compute_config_hash` in a coherent place.

**Affects:** `storage/results_exporter.py` (deleted), `storage/utils.py` (new), `report_runner.py`, `scenario_processor.py`.

---

## Data Models

### No New Models

No new Pydantic models are introduced. All types already exist.

### Modified: `LocalRunContext` — Add Typed Attributes

```python
class LocalRunContext(RunContext):
    def __init__(self, ...):
        # ... existing init ...
        
        # Step-communication slots (not storage abstractions)
        self.processor_results: Optional[List[OutputRecord]] = None
        self.evaluation_results: Optional[List[Dict[str, Any]]] = None
        self.test_subject: Optional[str] = None
        self.model_variant: Optional[str] = None
```

**Import addition** to `contexts.py`:
```python
from typing import Dict, List, Optional, Any  # Any already present
# OutputRecord already imported
```

### Unchanged On-Disk Schemas

| File | Change |
|------|--------|
| `results_raw.jsonl` | None — `OutputRecord.model_dump()` produces identical fields |
| `results_judged.jsonl` | Unchanged — `metadata` excluded via `model_dump(exclude={"metadata"})` |
| `manifest.json` | `variant_count` corrected from hardcoded `1` to `len(eval_config.variants)` |

---

## API & Interface Design

### `storage/utils.py` — New Module

```python
"""Storage utility functions for gavel-ai."""

import hashlib
from pathlib import Path
from typing import Dict


def compute_config_hash(config_files: Dict[str, Path]) -> str:
    """
    Compute SHA256 hash of configuration files.

    Args:
        config_files: Dict mapping config name to Path, sorted by key for stability.

    Returns:
        SHA256 hash as hex string.

    Raises:
        FileNotFoundError: If any config file does not exist.
    """
    hasher = hashlib.sha256()
    for key in sorted(config_files.keys()):
        path = config_files[key]
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "rb") as f:
            hasher.update(f.read())
    return hasher.hexdigest()
```

### `ScenarioProcessorStep.execute` — Updated Signature

No change to the external method signature. Internal changes only.

### `JudgeRunnerStep.execute` — Updated Behaviour

No change to the external method signature. Now accepts `List[OutputRecord]` in `context.processor_results` (was `List[ProcessorResult]`).

### `judge` CLI Command — Simplified

```
gavel oneshot judge --run RUN_ID [--eval EVAL_NAME]
```

- `--judges` option removed.
- Model resolution removed from CLI.
- Outputs same success message as before.

### Resolved Implementation Decisions

1. **Raw JSONL streaming**: Use `context.results_raw.append(record)` via `RecordDataSource`. Direct `jsonlines` file writes are forbidden — storage abstraction must be respected for non-filesystem backends.

2. **`--judges` filter**: Removed. Judge selection is controlled by `eval_config.test_subjects[].judges`.

3. **`metadata` in `results_judged.jsonl`**: Excluded. `metadata` is run-level context available in the run directory; writing it per-row is redundant. Use `record.model_dump(exclude={"metadata"})`.

---

## Implementation Patterns & Conventions

### Naming Conventions

Follow existing project conventions (unchanged):

| Construct | Convention | Example |
|-----------|-----------|---------|
| Functions/methods | `snake_case` | `compute_config_hash()` |
| Classes | `PascalCase` | `LocalRunContext` |
| JSON fields | `snake_case` | `"variant_id"` |

### Error Handling Pattern

No changes to the error handling approach. Use existing custom exceptions from `gavel_ai.core.exceptions`. Required checks:

- `JudgeRunnerStep`: raise `ConfigError` if `context.processor_results is None`.
- `ReportRunnerStep`: raise `ConfigError` if `context.processor_results is None`.
- `judge` CLI: raise `ResourceNotFoundError` if loaded records list is empty.
- `scenario_processor`: raise `ConfigError` if `eval_config.variants` is empty.

### Testing Pattern

All changed code paths must have unit tests. Use `unittest.mock.AsyncMock` for async step methods. Update mocks from `ProcessorResult` to `OutputRecord` where `context.processor_results` is involved.

**Key test cases to add or update:**

| Test file | Change |
|-----------|--------|
| `test_steps.py` | Replace `ProcessorResult` mocks with `OutputRecord` mocks in `ScenarioProcessorStep` tests; add multi-variant (2-variant) assertion |
| `test_report_runner.py` | Update to pass `List[OutputRecord]` in context; assert `results_judged.jsonl` join is on `(scenario_id, variant_id)` |
| `test_rejudge.py` | **Delete** |
| `test_judge_cli.py` (new or in existing) | Assert that `judge` command runs `JudgeRunnerStep` + `ReportRunnerStep` without model resolution |

**Coverage expectation:** All new/modified code paths covered. Deleted test file coverage gap must be covered by updated step tests.

---

## Security & Performance

### Security

| Concern | Mitigation |
|---------|-----------|
| File write safety | `jsonlines.open(mode="a")` is append-safe; one record per line, no file corruption |
| Input validation | `OutputRecord` is a Pydantic model; loaded from JSONL via `RecordDataSource` — validation at load time |
| No new attack surfaces | No new CLI args, no new external inputs |

### Performance

| Concern | Target | Approach |
|---------|--------|---------|
| Multi-variant latency | O(N×M) — linear in scenarios × variants | Sequential per-variant executor loop; no batching across variants |
| Memory | O(N×M) for `processor_results` list | Acceptable — same per-run budget as before, now multiplied by M variants |
| `results_raw.jsonl` streaming | Unchanged | Stream-per-result via `_spool_result`, same pattern |
| Judge execution | O(N×M×J) — linear in scenarios × variants × judges | One `execute_batch` call per variant group; unchanged sequential judge logic |

### Observability

- Existing OTel spans on LLM calls and judge evaluations are unchanged.
- Update log message in `ScenarioProcessorStep` to include `variant_count` and total record count.
- Update `manifest.json` `variant_count` to reflect actual variant count.

---

## Implementation Sequence

The dependency ordering is critical — the type change in `processor_results` touches every step.

1. **`storage/utils.py`** *(no dependencies — implement first)*
   - New file. Move `compute_config_hash` from `ResultsExporter`.
   - Verify existing callers (only `ReportRunnerStep`) are updated.

2. **`contexts.py` — typed attrs** *(blocking for all steps)*
   - Add `processor_results: Optional[List[OutputRecord]] = None` and the other three attrs.
   - Run `mypy` to catch any downstream type errors.

3. **`scenario_processor.py`** *(depends on 2)*
   - Add `_make_output_record` helper.
   - Add variant outer loop.
   - Replace `exporter.append_raw_result` with inline `OutputRecord` write.
   - Set `context.processor_results = List[OutputRecord]`.
   - Remove `ResultsExporter` import.

4. **`judge_runner.py`** *(depends on 2)*
   - Replace `zip(scenarios, processor_results)` with `scenario_map` + `groupby(variant_id)` + per-group `execute_batch`.
   - Import `defaultdict`.

5. **`report_runner.py`** *(depends on 1, 2)*
   - Replace `exporter.export_judged_results(...)` with inline `(scenario_id, variant_id)` join + `jsonlines.open` write.
   - Replace `exporter.compute_config_hash(...)` with `compute_config_hash(...)` from `storage.utils`.
   - Update `variant_count` in manifest to `len(eval_config.variants)`.
   - Remove `ResultsExporter` import.

6. **`cli/commands/oneshot.py`** *(depends on 2, 3, 4, 5)*
   - Rewrite `judge` command: load `OutputRecord` list, set context, run `JudgeRunnerStep` + `ReportRunnerStep`.
   - Remove `ReJudge` import and model resolution code.
   - Remove `--judges` option (or implement pre-filter if confirmed).

7. **Delete files** *(depends on 6)*
   - Delete `judges/rejudge.py`.
   - Delete `storage/results_exporter.py`.
   - Remove `ReJudge` from `judges/__init__.py`.
   - Delete `tests/unit/test_rejudge.py`.

8. **Update tests** *(parallel with 3–6)*
   - Update `test_steps.py` and `test_report_runner.py` for new types.
   - Add multi-variant test case.

**Parallel work opportunities:** Steps 3, 4, and 5 can be worked in parallel once step 2 (`contexts.py`) is complete. Step 7 (deletion) should be last, after all imports are cleaned up.

**Known implementation risks:**
- `RecordDataSource.append()` support: verify before implementing the spool pattern (see Open Question 1).
- `conversational_processor.py` uses `context.test_subject` and `context.model_variant` — adding typed attrs to `LocalRunContext` must not break the conversational path. Run the conversational unit tests after step 2.
