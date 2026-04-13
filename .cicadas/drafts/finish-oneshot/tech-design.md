
---
summary: "Nine targeted changes to the OneShot workflow. The largest is a new DeterministicMetric hierarchy (ClassifierMetric + RegressionMetric) — NOT Judge subclasses; they are pure GT comparisons with no LLM call, run by JudgeRunnerStep alongside but separately from JudgeExecutor. Supporting changes: TOML judge config resolution via config_ref, typed scaffolding templates, prompt snapshot, expanded validator, .workflow_status step tracking, score-averaging exclusion, deterministic report section, and in-situ scaffold fix. All changes are additive or narrow surgical fixes. No architectural shifts."
phase: "tech"
when_to_load:
  - "When implementing or reviewing architecture, interfaces, data models, conventions, and sequencing."
  - "When checking whether changes still conform to the agreed technical approach."
depends_on:
  - "prd.md"
  - "ux.md"
modules:
  - "src/gavel_ai/judges"
  - "src/gavel_ai/core/steps"
  - "src/gavel_ai/core/contexts.py"
  - "src/gavel_ai/cli/commands/oneshot.py"
  - "src/gavel_ai/cli/scaffolding.py"
  - "src/gavel_ai/reporters/oneshot_reporter.py"
  - "src/gavel_ai/reporters/templates/oneshot.html"
  - "src/gavel_ai/models/runtime.py"
  - "src/gavel_ai/models/config.py"
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

# Tech Design: finish-oneshot

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

Nine changes to the OneShot pipeline. All are additive or narrow surgical fixes. The heaviest change is the `DeterministicMetric` hierarchy: a new class family entirely separate from `Judge`. `ClassifierMetric` and `RegressionMetric` are pure GT comparisons — no LLM call, no `JudgeResult`. They accumulate per-sample `(prediction, actual)` pairs and expose a `compute()` method that returns a `DeterministicRunResult`. `JudgeRunnerStep` runs them in a separate loop alongside `JudgeExecutor`, then stores results on `context.deterministic_metrics`. Everything else is simpler: TOML file loading, additional snapshot copy, re-enabled validator checks, a JSONL status file, score averaging exclusions, a report section, and an in-situ scaffold fix.

### Cross-Cutting Concerns

1. **DeterministicMetric is not a Judge** — `ClassifierMetric` and `RegressionMetric` do not extend `Judge`, do not use `JudgeResult`, and do not go through `JudgeExecutor`. They are registered in `JudgeRegistry` for discoverability but have their own execution path in `JudgeRunnerStep`.
2. **RunContext attribute pattern** — Short-lived per-run state (`processor_results`, `evaluation_results`, `test_subject`) is stored as typed attributes on `LocalRunContext`, not in the ABC. `deterministic_metrics` follows this same pattern.
3. **Immutability of `results_raw.jsonl`** — Deterministic metric per-sample data must NOT be written to `results_raw.jsonl`. It flows through `context.deterministic_metrics` → `RunData` → reporter only.
4. **OTel spans** — `DeterministicMetric.evaluate_sample()` must emit OTel spans.

### Brownfield Notes

- `JudgeConfig` already has `config_ref: Optional[str]` — use it for TOML references. Do not overload `config: Optional[Dict]` with string values.
- `ValidatorStep` has two commented-out blocks (variant resolution, scenario count check). Re-enable and fix them. Do not delete the comment blocks until after tests pass — they explain the original reasoning.
- `LocalRunContext.snapshot_run_config()` exists and works for 3 files. Extend it, don't replace it.
- `StepPhase` enum in `core/steps/base.py`. `PREPARE` value is new.
- `JudgeResult.score: int ge=1, le=10` — unchanged. Deterministic metrics never produce a `JudgeResult`.

---

## Tech Stack & Dependencies

| Category | Selection | Rationale |
|----------|-----------|-----------|
| Language | Python 3.13 | Existing |
| CLI | Typer | Existing |
| Config parsing | Pydantic | Existing |
| Reporting | Jinja2 | Existing |
| TOML parsing | `tomllib` (stdlib, Python 3.11+) | Zero new dependency; already available |
| Deterministic metrics | scikit-learn | Industry standard for classification/regression metrics; no viable lighter alternative |

**New dependencies introduced:**
- `scikit-learn>=1.4,<2.0` — population metrics for `ClassifierMetric` and `RegressionMetric`. Chosen over implementing metrics manually to get consistent, tested implementations of edge cases (e.g., `fbeta`, `cohen_kappa`).

**Dependencies explicitly rejected:**
- `numpy` (standalone) — scikit-learn pulls it transitively; no direct import needed.
- `polars` / `pandas` — no dataframe operations required; plain lists suffice.

---

## Project / Module Structure

Only new or modified files shown:

```
src/gavel_ai/
├── judges/
│   ├── deterministic_metric.py     # NEW: DeterministicMetric base, ClassifierMetric, RegressionMetric
│   ├── judge_executor.py           # UNCHANGED
│   └── judge_registry.py          # MODIFIED: register "classifier" and "regression" (for discovery/validation)
├── core/
│   ├── contexts.py                # MODIFIED: snapshot prompts + snapshot_metadata.json; mark_step_complete/get_completed_steps on LocalRunContext; get_judge_config(name) on LocalFileSystemEvalContext
│   └── steps/
│       ├── base.py                # MODIFIED: StepPhase.PREPARE; safe_execute calls mark_step_complete on success
│       ├── validator.py           # MODIFIED: re-enable variant resolution, prompt existence, judge type warnings, scenario count
│       ├── judge_runner.py        # MODIFIED: split judges into LLM (→ JudgeExecutor) and deterministic (→ inline loop); set context.deterministic_metrics
│       └── report_runner.py       # MODIFIED: pass deterministic_metrics + processor_results into RunData
├── models/
│   ├── runtime.py                 # MODIFIED: add DeterministicRunResult, PerSampleDeterministicResult; add deterministic_results to ReportData
│   └── config.py                  # NO CHANGE: config_ref field already exists on JudgeConfig
├── reporters/
│   ├── oneshot_reporter.py        # MODIFIED: add deterministic_results section; skip error scores from LLM average; add skipped_count
│   └── templates/
│       └── oneshot.html           # MODIFIED: add Deterministic Judges section; (N skipped) annotations
└── cli/
    ├── commands/
    │   └── oneshot.py             # MODIFIED: add --template option to create()
    └── scaffolding.py             # MODIFIED: dispatch on template; generate classification/regression templates; write example quality_judge.toml; fix in-situ eval_config
tests/
└── unit/
    └── judges/
        └── test_deterministic_judge.py   # NEW: unit tests for ClassifierMetric, RegressionMetric
```

**Key structural decisions:**
- `DeterministicJudge` lives in its own file (`deterministic_judge.py`) — it's a peer to `deepeval_judge.py`, not a submodule of it.
- Registration of `"classifier"` and `"regression"` happens at module load time in `deterministic_judge.py` (same pattern as `deepeval_judge.py`).

---

## Architecture Decisions (ADRs)

### ADR-1: DeterministicMetric is a separate class hierarchy, not a Judge subclass

**Decision:** `ClassifierMetric` and `RegressionMetric` extend `DeterministicMetric`, which does NOT extend `Judge`. They have no `evaluate()` method returning `JudgeResult`. Instead:
- `evaluate_sample(scenario: Scenario, processor_output: str) -> PerSampleDeterministicResult` — synchronous, pure Python, no LLM call. Extracts prediction via dotted-path from `processor_output` (parsed as JSON dict) and actual via dotted-path from `scenario` dict. Accumulates the pair internally. Returns `PerSampleDeterministicResult`.
- `compute() -> DeterministicRunResult` — called once after all samples, computes population metric via scikit-learn from accumulated pairs.

`JudgeRunnerStep.execute()` splits the judge list from `eval_config` into LLM judges (pass to `JudgeExecutor` as today) and deterministic metrics (run via a separate inline loop). After both loops, it serializes `DeterministicRunResult` objects into `context.deterministic_metrics: Dict[str, DeterministicRunResult]`.

`JudgeRegistry` still registers `"classifier"` → `ClassifierMetric` and `"regression"` → `RegressionMetric` so the validator can check type registration — but `JudgeRegistry.create()` returns a `DeterministicMetric` instance, not a `Judge`. `JudgeRunnerStep` uses `isinstance(metric, DeterministicMetric)` to route.

**Rationale:** Deterministic metrics are not judges. There is no LLM call, no reasoning string, no score in the 1–10 sense. Forcing them into `JudgeResult` would require either clamping unbounded regression errors (corrupts population metric inputs) or inventing a sentinel score (misleads readers of `results_judged.jsonl`). A separate class hierarchy makes the distinction explicit and eliminates all the semantic gymnastics.

**Alternative rejected:** `DeterministicJudge extends Judge` with sentinel scores — adds complexity and produces misleading score fields in output artifacts.

**Affects:** `deterministic_metric.py` (new), `judge_registry.py`, `judge_runner.py`, `models/runtime.py`, `report_runner.py`, `oneshot_reporter.py`.

---

### ADR-2: DeterministicMetric execution is an inline loop in JudgeRunnerStep; no changes to JudgeExecutor

**Decision:** `JudgeRunnerStep.execute()` is extended to:
1. Partition `judges_list` into `llm_judges` and `det_metrics` using `isinstance(JudgeRegistry.create(cfg), DeterministicMetric)`.
2. Pass `llm_judges` to `JudgeExecutor` as today — no change to that path.
3. For `det_metrics`: instantiate each, loop over all `processor_results` in scenario order, call `metric.evaluate_sample(scenario, output)` synchronously per sample, then call `metric.compute()` to get the `DeterministicRunResult`. Store all results in `context.deterministic_metrics`.

**Rationale:** Deterministic metric execution is cheap and synchronous. Adding a second executor class adds indirection for no benefit. Keeping it inline in `JudgeRunnerStep` keeps the execution boundary clear and the call sequence explicit. `JudgeExecutor` is unchanged.

**Alternative rejected:** Adding a `DeterministicMetricExecutor` — unnecessary abstraction for what is a simple loop.

**Affects:** `judge_runner.py` only (plus the new `deterministic_metric.py`).

---

### ADR-3: External TOML config uses existing config_ref field; JudgeRunnerStep resolves before passing to JudgeExecutor

**Decision:** `JudgeConfig.config_ref: Optional[str]` already exists. When `JudgeRunnerStep` processes judges, before passing to `JudgeExecutor`, it checks each `judge_config.config_ref`. If set, it calls `eval_ctx.get_judge_config(config_ref)` which loads `config/judges/{name}.toml` via `tomllib`. The result (a dict with `criteria`, `evaluation_steps`, `threshold`) is merged into `judge_config.config`. `LocalFileSystemEvalContext.get_judge_config()` is a new method, sibling to the existing `get_judge()` (which reads `.json`).

**Rationale:** `config_ref` is the existing field designed for this purpose. Using it avoids overloading `config: Optional[Dict]` with ambiguous string/dict union types that Pydantic would reject. TOML is stdlib in Python 3.11+ (`tomllib`), so no new dependency.

**Alternative rejected:** Overloading `config` to accept either a dict or a string — Pydantic would need `Union[Dict, str]`, which changes model validation behavior for existing configs.

**Affects:** `contexts.py`, `judge_runner.py`, `scaffolding.py`.

---

### ADR-4: .workflow_status is a new method pair on RunContext ABC + LocalRunContext; safe_execute() calls it unconditionally

**Decision:** Add two abstract methods to `RunContext` ABC: `mark_step_complete(phase: StepPhase)` and `get_completed_steps() -> List[StepPhase]`. `LocalRunContext` implements these by appending/reading a JSONL file at `{run_dir}/.workflow_status`. `Step.safe_execute()` calls `context.mark_step_complete(self.phase)` immediately after a successful `execute()` call. `LocalRunContext.__init__()` writes a `PREPARE` entry after `snapshot_run_config()` completes.

**Rationale:** Putting the methods on the ABC ensures any future `RunContext` implementation (e.g., cloud-based) also tracks step completion. The JSONL format is append-only, human-readable, and consistent with all other artifact files. Calling `mark_step_complete` inside `safe_execute()` — the error-catching wrapper — ensures it is only called on success.

**Alternative rejected:** Writing `.workflow_status` from within each `Step.execute()` implementation — duplicates boilerplate across all step classes and risks being forgotten in future steps.

**Affects:** `contexts.py`, `core/steps/base.py`, `RunContext` ABC contract.

---

### ADR-5: Score averaging exclusion via processor_errors_map built in OneShotReporter

**Decision:** `ReportRunnerStep` adds `processor_results` to `RunData` as a new field (`raw_results: List[Dict]`). `OneShotReporter._build_context()` builds a `processor_errors: Dict[(scenario_id, variant_id), bool]` lookup from `raw_results`. When accumulating judge scores in the summary metrics loop, it skips entries where `processor_errors.get((scenario_id, variant_id))` is truthy. A `skipped_count` dict tracks exclusions per `(variant, judge)` for report display.

**Rationale:** `OutputRecord.error` is the authoritative signal for a failed processor step. Routing it through `RunData` is the cleanest path to the reporter without changing `EvaluationResult` or `JudgeEvaluation` schemas. The reporter already iterates `processor_results` implicitly (via `evaluation_results`) — surfacing it explicitly as `raw_results` makes the join intentional.

**Alternative rejected:** Adding `processor_error: Optional[str]` to `EvaluationResult` — requires schema change and migration path; overkill for what is a display-only concern.

**Affects:** `report_runner.py`, `oneshot_reporter.py`, `reporters/templates/oneshot.html`.

---

### ADR-6: Validator re-enables variant resolution for local evals only, gated by test_subject_type

**Decision:** The commented-out variant resolution block in `ValidatorStep` is re-enabled, guarded by `if eval_config.test_subject_type == "local":`. In-situ evals skip variant model resolution entirely (no local model required). Prompt existence check also gates on `test_subject_type == "local"`.

**Rationale:** The original comment says `# TODO: remove this or refactor to handle in-situ` — the correct resolution is the gate, not permanent deletion. In-situ evals reference remote systems, not local model definitions.

**Affects:** `core/steps/validator.py`.

---

## Data Models

### New Models

```python
# src/gavel_ai/models/runtime.py

class PerSampleDeterministicResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scenario_id: str
    prediction: str
    actual: str
    # ClassifierMetric: True = match, False = mismatch (per class)
    # RegressionMetric: unbounded signed float (prediction - actual)
    raw_score: Optional[float] = None
    match: Optional[bool] = None       # ClassifierMetric only
    skip_reason: Optional[str] = None

class DeterministicRunResult(BaseModel):
    """Population-level result for one DeterministicMetric across all samples."""
    model_config = ConfigDict(extra="ignore")
    metric_name: str
    report_metric: str
    population_score: Optional[float] = None   # None if all samples skipped
    per_sample: List[PerSampleDeterministicResult] = Field(default_factory=list)
```

### Modified Models

| Model | Change | Migration Required? |
|-------|--------|-------------------|
| `ReportData` | Add `deterministic_results: List[DeterministicRunResult] = []` | No — additive, default empty |
| `RunContext` ABC | Add abstract `mark_step_complete()` and `get_completed_steps()` | No — additive; no storage schema change |

### RunData (report_runner.py)

```python
@dataclass
class RunData:
    metadata: Dict[str, Any] = field(default_factory=dict)
    results: List[Dict[str, Any]] = field(default_factory=list)
    raw_results: List[Dict[str, Any]] = field(default_factory=list)         # NEW: for error exclusion
    deterministic_metrics: Optional[Dict[str, DeterministicRunResult]] = None  # NEW
    telemetry: Dict[str, Any] = field(default_factory=dict)
```

---

## API & Interface Design

### New: DeterministicMetric base class

```python
# src/gavel_ai/judges/deterministic_metric.py

class DeterministicMetric(ABC):
    """Base class for GT-comparison metrics. Not a Judge — no LLM call, no JudgeResult."""

    def __init__(self, config: JudgeConfig) -> None:
        self.config = config
        self._sample_data: List[PerSampleDeterministicResult] = []
        self.tracer = get_tracer(__name__)

    @abstractmethod
    def evaluate_sample(self, scenario: Scenario, processor_output: str) -> PerSampleDeterministicResult:
        """
        Synchronous. Extract prediction and actual via dotted-path.
        Append result to self._sample_data. Return PerSampleDeterministicResult.
        On parse failure or missing field: return result with skip_reason set.
        """
        ...

    @abstractmethod
    def compute(self) -> DeterministicRunResult:
        """
        Compute population metric from self._sample_data (excluding skipped entries).
        Returns DeterministicRunResult with population_score=None if all samples skipped.
        """
        ...


class ClassifierMetric(DeterministicMetric):
    """Per-sample: match (T) or mismatch (F) per class. Population: scikit-learn classifier metric."""

class RegressionMetric(DeterministicMetric):
    """Per-sample: signed error (prediction - actual), unbounded float. Population: scikit-learn regression metric."""
```

### JudgeExecutor — unchanged

No modifications to `JudgeExecutor`. Deterministic metrics bypass it entirely.

### Modified: JudgeRunnerStep.execute() — routing logic

```python
# Partition judge configs
llm_judge_configs = []
det_metric_configs = []
for cfg in judges_list:
    instance = JudgeRegistry.create(cfg)
    if isinstance(instance, DeterministicMetric):
        det_metric_configs.append((cfg, instance))
    else:
        llm_judge_configs.append(cfg)

# LLM judges — existing path, unchanged
if llm_judge_configs:
    executor = JudgeExecutor(llm_judge_configs, ...)
    all_results = await executor.execute_batch(...)
    context.evaluation_results = [r.model_dump() for r in all_results]

# Deterministic metrics — inline loop, synchronous
det_results: Dict[str, DeterministicRunResult] = {}
for cfg, metric in det_metric_configs:
    for record in processor_results:
        scenario = scenario_map[record.scenario_id]
        metric.evaluate_sample(scenario, record.processor_output)
    det_results[cfg.name] = metric.compute()
context.deterministic_metrics = det_results
```

### Modified: LocalFileSystemEvalContext

```python
def get_judge_config(self, name: str) -> Dict[str, Any]:
    """
    Load and parse config/judges/{name}.toml.
    Fields: criteria, evaluation_steps, threshold.
    Raises ConfigError if file not found.
    Uses tomllib (stdlib).
    """
    ...
```

### Modified: RunContext ABC

```python
@abstractmethod
def mark_step_complete(self, phase: StepPhase) -> None:
    """Append completed step to .workflow_status."""

@abstractmethod
def get_completed_steps(self) -> List[StepPhase]:
    """Read .workflow_status and return completed phases."""
```

### Modified: Step.safe_execute()

```python
async def safe_execute(self, context: RunContext) -> bool:
    try:
        await self.execute(context)
        context.mark_step_complete(self.phase)   # NEW: only on success
        return True
    except ...:
        ...
```

### CLI: gavel oneshot create --template

```
gavel oneshot create --eval NAME [--type local|in-situ] [--template default|classification|regression]

--template: Scaffold template to use.
  default        Standard eval with GEval quality judge (default)
  classification Deterministic ClassifierMetric judges (accuracy + f1), 3 sample scenarios
  regression     Deterministic RegressionMetric judge (mean_absolute_error), 3 numeric scenarios
```

### Backward Compatibility

- All existing `JudgeConfig` fields unchanged. `config_ref` was already present but unused.
- `RunData` additions are backward-compatible (new optional fields with defaults).
- `ReportData.deterministic_results` has an empty-list default — existing reports unaffected.
- `mark_step_complete`/`get_completed_steps` are new ABC methods. All existing `RunContext` subclasses must implement them. Only `LocalRunContext` exists today, so no hidden subclass impact.

---

## Implementation Patterns & Conventions

### Naming Conventions

| Construct | Convention | Example |
|-----------|-----------|---------|
| Functions/Methods | `snake_case` | `finalize_deterministic_judges()` |
| Classes | `PascalCase` | `ClassifierMetric`, `DeterministicJudge` |
| ClassVar flags | `snake_case` | `is_deterministic` |
| Judge type keys | `snake_case.dot.separated` | `"classifier"`, `"regression"` |
| JSONL fields | `snake_case` | `"completed_at"`, `"raw_score"` |

### DeterministicMetric Pattern

Per-sample `evaluate_sample()` must:
1. Try to parse `processor_output` as JSON dict. On failure: append `PerSampleDeterministicResult(skip_reason="outputs is not a dict")` to `self._sample_data` and return it.
2. Try dotted-path lookup for `prediction_field`. On failure: append with `skip_reason="prediction_field not found: <path>"`.
3. Try dotted-path lookup for `actual_field` in `scenario.__dict__` / `scenario.metadata`. On failure: append with `skip_reason`.
4. For **ClassifierMetric**: set `match = (prediction.strip().lower() == actual.strip().lower())`, `raw_score = None`.
5. For **RegressionMetric**: set `raw_score = float(prediction) - float(actual)` (unbounded), `match = None`.
6. Append and return the result.

`compute()` must filter `self._sample_data` to exclude entries with `skip_reason` set before passing pairs to scikit-learn. If zero valid samples remain, return `DeterministicRunResult(population_score=None, ...)`.

### Error Handling Pattern

```python
# TOML config resolution in JudgeRunnerStep
if judge_config.config_ref:
    try:
        toml_config = context.eval_context.get_judge_config(judge_config.config_ref)
        judge_config.config = judge_config.config or {}
        judge_config.config.update(toml_config)
    except ConfigError as e:
        raise ConfigError(
            f"Judge config file not found: config/judges/{judge_config.config_ref}.toml "
            f"— Create the file or remove the config_ref field"
        ) from e
```

All errors follow: `ConfigError("What failed — How to fix it")`. Never raise bare `FileNotFoundError` or `KeyError` to the user.

### Testing Pattern

```python
@pytest.mark.unit
class TestClassifierMetric:
    def test_matching_labels_score_10(self):
        ...
    def test_mismatched_labels_score_1(self):
        ...
    def test_case_insensitive_match(self):
        ...
    def test_skip_on_non_json_output(self):
        ...
    def test_skip_on_missing_prediction_field(self):
        ...
    def test_population_metric_accuracy(self):
        ...
    def test_population_metric_all_skipped_returns_none(self):
        ...
```

Coverage expectations: 100% on `DeterministicJudge`, `ClassifierMetric`, `RegressionMetric`. Unit tests use no LLM mocks and no filesystem.

### OTel Spans

`DeterministicJudge.evaluate()` must emit a span using the inherited `self.tracer`. Span name: `"deterministic_judge.evaluate"`. Attributes: `judge.name`, `judge.type`, `scenario.id`, `judge.skipped` (bool).

---

## Security & Performance

### Security

| Concern | Mitigation |
|---------|-----------|
| TOML path traversal | `get_judge_config(name)` constructs path as `config_dir / "judges" / f"{name}.toml"`. `name` comes from `eval_config.json`, not user input at runtime. No shell execution, no symlink traversal. |
| scikit-learn input | All inputs to scikit-learn metric functions are lists of Python strings/floats derived from scenario data. No user-controlled format strings. |
| `.workflow_status` write | Append-only JSONL; never executed. |

### Performance

| Concern | Target | Approach |
|---------|--------|---------|
| Per-sample deterministic overhead | < 1 ms / sample | No I/O in `evaluate()`. Dotted-path lookup is O(depth). |
| Population metric computation | < 100 ms for ≤ 1000 samples | scikit-learn in-process, synchronous, one-shot after batch. |
| Prompt snapshot copy | No regression on run init time | `shutil.copytree` on `config/prompts/`; typical prompt dirs are < 50 KB. |
| TOML config load | Cached in `_judge_config_cache` on `LocalFileSystemEvalContext` | Consistent with existing `_prompt_cache` / `_judge_cache` patterns. |

### Observability

- **`.workflow_status`**: Writable by `LocalRunContext`. Readable by CI operators and future tooling.
- **OTel spans**: `DeterministicMetric.evaluate_sample()` emits spans with `metric.skipped` attribute — allows filtering skipped evaluations in tracing tools.
- **Snapshot log line**: `LocalRunContext.snapshot_run_config()` logs at INFO level after copying prompts: `Config snapshot saved (prompts included: N files)`.

---

## Implementation Sequence

1. **Foundation — Data models and Judge base** *(blocking)*
   - Add `PerSampleDeterministicResult`, `DeterministicJudgeResult` to `models/runtime.py`
   - Add `deterministic_results` field to `ReportData`
   - Add `is_deterministic: ClassVar[bool] = False` to `Judge` base class in `judges/base.py`
   - Add `PREPARE` to `StepPhase` enum in `core/steps/base.py`
   - Add abstract `mark_step_complete` / `get_completed_steps` to `RunContext` ABC

2. **OS-1 — DeterministicMetric, ClassifierMetric, RegressionMetric** *(depends on 1)*
   - Create `judges/deterministic_metric.py` with base class and two implementations
   - Register in `judge_registry.py` (for validator discovery only)
   - Add `scikit-learn` to `pyproject.toml`
   - Write unit tests in `tests/unit/judges/test_deterministic_metric.py`

3. **OS-1 — JudgeRunnerStep routing** *(depends on 2)*
   - Add deterministic metric partition + inline loop to `JudgeRunnerStep.execute()`
   - Set `context.deterministic_metrics`
   - `JudgeExecutor` unchanged

4. **OS-4 / OS-6 — Snapshot + step tracking** *(depends on 1; parallel with 2–3)*
   - Extend `LocalRunContext.snapshot_run_config()` to copy prompts + write `snapshot_metadata.json`
   - Implement `mark_step_complete()` / `get_completed_steps()` on `LocalRunContext`
   - Modify `Step.safe_execute()` to call `mark_step_complete` on success

5. **OS-2 — External TOML judge config** *(depends on 1)*
   - Add `get_judge_config()` to `LocalFileSystemEvalContext`
   - Modify `JudgeRunnerStep` to resolve `config_ref` before passing to `JudgeExecutor`
   - Update scaffold to write example `config/judges/quality_judge.toml`

6. **OS-5 — Expanded validator** *(depends on 1)*
   - Re-enable variant resolution (gated on `test_subject_type == "local"`)
   - Add prompt existence check (gated on `test_subject_type == "local"`)
   - Add judge type warning
   - Re-enable scenario count check

7. **OS-7 / OS-8 — Reporter changes** *(depends on 3)*
   - Modify `ReportRunnerStep` to pass `raw_results` and `deterministic_metrics` into `RunData`
   - Modify `OneShotReporter._build_context()` for score averaging exclusion + deterministic routing
   - Add `DeterministicJudgeResult` population to `ReportData.deterministic_results`
   - Extend `oneshot.html` with deterministic judge section and `(N skipped)` annotations

8. **OS-3 / OS-9 — Scaffold templates + in-situ fix** *(parallel with 4–7)*
   - Add `--template` option to `oneshot create`
   - Add `_generate_classification_templates()` and `_generate_regression_templates()` in `scaffolding.py`
   - Fix `generate_eval_config()` for `eval_type == "in-situ"`

**Parallel work opportunities:**
- Steps 2 and 4 are independent — can be implemented by separate branches simultaneously.
- Step 8 is fully independent of all others.
- Steps 5 and 6 are independent of each other.

**Known implementation risks:**
- `tomllib` is only available in Python 3.11+. Verify the project's minimum Python version (`pyproject.toml` shows 3.10+). If 3.10 support is required, add `tomli` as a conditional dependency. **Spike needed**: check `pyproject.toml` `requires-python` field before starting step 5.
