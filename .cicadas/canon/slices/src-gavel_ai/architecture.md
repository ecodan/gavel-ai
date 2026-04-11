## System Architecture

The core of Gavel-AI follows a **Service-Oriented Design** utilizing abstract base classes to define clear contracts for different evaluation activities.

### Component Map

- **Workflows (`core/workflows/`)**: Top-level orchestrators per evaluation mode.
  - `OneShotWorkflow`: Composes Validator → ScenarioProcessor → JudgeRunner → ReportRunner steps.
  - Conversational workflow: Composes similar steps with multi-turn, multi-variant execution.
- **Steps (`core/steps/`)**: Discrete, composable units of work. Each implements `safe_execute(ctx) -> bool`.
  - `ScenarioProcessorStep`, `JudgeRunnerStep`, `ReportRunnerStep`, `ValidatorStep`.
  - `ConversationalProcessorStep`: Executes multi-turn conversations with `max_turns`/`max_duration_ms` enforcement.
- **Processors (`processors/`)**: Lower-level domain logic invoked by Steps.
  - `PromptProcessor`: Single-turn LLM invocation with retry backoff.
  - `ScenarioProcessor`: Deep-copies input scenarios to prevent mutation.
  - `ClosedBoxProcessor`: External system integration with typed exception handling.
- **Judging Layer (`judges/`)**: A registry of evaluation algorithms. Judges are decoupled from the models being tested, allowing for independent re-judging via `ReJudge`.
- **Storage Layer (`storage/`)**: Abstracts filesystem interactions. `RunContext`/`LocalRunContext` is the primary interface for saving and loading run artifacts.
- **Reporters (`reporters/`)**: `OneShotReporter` extends `Jinja2Reporter` and converts `EvaluationResult` objects into `ReportData` (Unified Reporting Spec v1.0) before template rendering.

### Inversion of Control

- **ProviderFactory**: Decouples the core engine from specific LLM providers. All LLM calls pass through Pydantic-AI wrapper classes created by this factory.
- **Registry Pattern**: Judges are registered and looked up by `type` field via `JudgeRegistry`.

### Key Data Flow (OneShot)

```
CLI run → OneShotWorkflow.execute()
  → LocalRunContext (creates run_id, sets up dirs)
  → ValidatorStep (reads eval_config.json + scenarios.jsonl)
  → ScenarioProcessorStep (calls PromptProcessor per scenario, writes results_raw.jsonl)
  → JudgeRunnerStep (runs judges, writes results_judged.jsonl)
  → ReportRunnerStep (OneShotReporter → report.html)
```

### Error Handling

- `conversational/errors.py`: `ConversationalError` hierarchy with `classify_error(e) -> (type, is_transient)`.
- `core/execution/retry_logic.py`: `retry_with_backoff(fn, max_retries, base_delay)` — async exponential backoff for transient LLM errors.
