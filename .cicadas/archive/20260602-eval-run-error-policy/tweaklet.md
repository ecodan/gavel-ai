---
summary: "Three-tier issue classification (ERROR/WARNING/OK) for task/judge execution with fail-fast exit_on_error/exit_on_warning policy on EvalConfig"
phase: "tasks"
when_to_load:
  - "When implementing eval-run-error-policy on tweak/eval-run-error-policy"
modules:
  - "src/gavel_ai/models/config.py"
  - "src/gavel_ai/core/issue_classifier.py (new)"
  - "src/gavel_ai/core/steps/base.py"
  - "src/gavel_ai/core/steps/scenario_processor.py"
  - "src/gavel_ai/core/workflows/oneshot.py"
---

# Tweaklet: eval-run-error-policy

## Intent

Introduce a three-tier issue classification system (ERROR / WARNING / OK) and
per-eval policy flags (`exit_on_error`, `exit_on_warning`) so that non-fatal
issues — like provider deprecation warnings or schema validation failures — do
not abort a run, while genuine LLM API failures remain fatal by default.

**Motivating problems:**
- A 429 Too Many Requests (or any 4xx/5xx) from an LLM provider during scenario
  execution or judging terminates the entire run with no policy override; should
  be classifiable and controllable.
- Schema validation failures and other non-fatal issues during task/judge execution
  should be demotable to WARNING so runs can continue rather than abort.

## Proposed Change

### 1. `ErrorPolicy` model + `EvalConfig` wiring (`models/config.py`)

Add a nested `ErrorPolicy` Pydantic model and attach it to `EvalConfig`:

```python
class ErrorPolicy(BaseModel):
    exit_on_error: bool = True    # halt run on ERROR-class issues
    exit_on_warning: bool = False # halt run on WARNING-class issues
```

Add to `EvalConfig`:
```python
error_policy: ErrorPolicy = Field(default_factory=ErrorPolicy)
```

JSON key: `"error_policy"`. Fully optional — existing configs get defaults.

### 2. `IssueClassifier` (`core/issue_classifier.py`, new file)

Single function:
```python
def classify(exc: BaseException) -> Literal["ERROR", "WARNING", "OK"]
```

Classification rules (checked in order):

| Condition | Tier |
|---|---|
| HTTP status 4xx or 5xx in exception message or attrs | `ERROR` |
| `ProcessorError` whose message contains "429", "rate limit", "too many" | `ERROR` |
| Schema/validation error (`ValidationError`, `ConfigError`) during task/judge execution | `WARNING` |
| Any other `Exception` during task/judge execution | `ERROR` |

### 3. `Step.safe_execute()` (`core/steps/base.py`)

Accept `error_policy: ErrorPolicy` (default `ErrorPolicy()`). After catching an
exception:
1. Call `classify(exc)` → tier.
2. Log at appropriate level: ERROR-tier → `logger.error`, WARNING-tier → `logger.warning`.
3. Store tier on `context.last_step_error_tier`.
4. Return `False` on ERROR (existing behaviour), but on WARNING return `True` with
   error recorded — the step is considered non-fatal.

### 4. `ScenarioProcessorStep` (`core/steps/scenario_processor.py`)

Per-scenario error handling:
- On a per-scenario exception, classify it.
- ERROR tier + `exit_on_error=True` → populate `OutputRecord.error`, halt
  immediately (existing behaviour).
- ERROR tier + `exit_on_error=False` → populate `OutputRecord.error`, continue to
  next scenario (skip this one).
- WARNING tier + `exit_on_warning=False` → populate `OutputRecord.error` with
  `"[WARNING] ..."` prefix, continue to next scenario.
- WARNING tier + `exit_on_warning=True` → populate `OutputRecord.error`, halt
  immediately (fail-fast, same as ERROR + exit_on_error to avoid wasting resources).

### 5. `OneShotWorkflow` (`core/workflows/oneshot.py`)

Pass `eval_ctx.eval_config.error_policy` down to steps that need it. No other
changes to orchestration logic.

### 6. New exception `RunPolicyError` (`core/exceptions.py`)

Raised immediately when a classified issue exceeds the configured policy threshold.
Caught at the CLI layer and displayed in the Rich error panel like other terminal errors.

## Acceptance Criteria

- `eval_config.json` with no `error_policy` block works identically to today.
- `error_policy: { exit_on_error: false }` causes per-scenario LLM 4xx/5xx errors
  to be recorded in `OutputRecord.error` and skipped rather than aborting the run.
- `error_policy: { exit_on_warning: true }` causes a run to halt immediately on
  the first WARNING-tier issue (fail-fast).
- Unit tests cover `classify()` for each tier, `exit_on_error=False` skip
  behaviour, and `exit_on_warning=True` halt behaviour.

## Tasks

- [x] Add `ErrorPolicy` to `models/config.py` and wire into `EvalConfig` <!-- id: 10 -->
- [x] Create `core/issue_classifier.py` with `classify()` function and unit tests <!-- id: 11 -->
- [x] Add `RunPolicyError` to `core/exceptions.py` <!-- id: 12 -->
- [x] Update `Step.safe_execute()` to use policy and tier-appropriate logging <!-- id: 13 -->
- [x] Update `ScenarioProcessorStep` per-scenario error handling <!-- id: 14 -->
- [x] Thread `error_policy` through `OneShotWorkflow` <!-- id: 15 -->
- [x] Integration test: `exit_on_error=False` completes run with partial errors <!-- id: 16 -->
- [x] Significance check: update canon if warranted <!-- id: 17 -->
