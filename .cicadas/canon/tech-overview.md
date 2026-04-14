# Tech Overview

> Canon document. Updated by the Synthesis agent at the close of each initiative.

## What This Is

Gavel-AI is a Python-based CLI evaluation engine that follows a clean architecture pattern. It orchestrates the flow from configuration loading and scenario execution via LLM providers to automated judging and HTML/Markdown reporting.

---

## Tech Stack

| Category | Selection | Notes |
|----------|-----------|-------|
| **Language/Runtime** | Python 3.10+ | Supported versions up to 3.13. |
| **CLI Framework** | Typer | Hierarchical command structure built on Click. |
| **LLM Abstraction** | Pydantic-AI | Swappable providers (Claude, GPT, Gemini, Ollama). |
| **Evaluation/Judges** | DeepEval + scikit-learn | LLM-as-judge (GEval) and deterministic GT-comparison metrics (accuracy, F1, MAE, etc.). |
| **Reporting** | Jinja2 | Template-based HTML and Markdown report generation. |
| **Observability** | OpenTelemetry | Native instrumentation for distributed tracing. |
| **Configuration** | Pydantic | Type-safe config schemas and field validation. |
| **Storage** | Filesystem-based | JSON/JSONL artifacts with a modular storage interface. |

---

## Project Structure

```
gavel-ai/
├── src/gavel_ai/          # Source code root
│   ├── cli/               # Typer commands and CLI presentation logic
│   ├── core/              # Shared models, exceptions, and base interfaces
│   ├── processors/        # Execution logic (OneShot, Conversational, Autotune)
│   ├── judges/            # Judge implementations and DeepEval adapters
│   ├── reporters/         # Jinja2 rendering and reporting templates
│   ├── storage/           # Persistence layer (RunContext, filesystem)
│   ├── providers/         # LLM provider factory and abstraction layer
│   └── telemetry/         # OpenTelemetry setup and instrumentation
├── tests/                 # unit and integration tests
├── docs/                  # Human-readable documentation
└── _bmad/                 # BMM-specific infrastructure
```

---

## Architecture

### System Design

Gavel-AI uses a **Layered Service Architecture** centered around the **RunContext** abstraction. The system is designed to be pluggable, allowing developers to swap out storage backends, judges, or LLM providers without modifying the core orchestrator. All execution state is persisted to the filesystem to ensure transparency and reproducibility.

### Key Components

| Component | Responsibility | Key Files |
|-----------|----------------|-----------|
| **Executor** | Orchestrates the end-to-end evaluation flow. | `src/gavel_ai/core/executor.py` |
| **Processor** | Implements specific workflow logic (e.g., OneShot). | `src/gavel_ai/processors/` |
| **Judge** | Evaluates LLM output against a scenario (LLM-based via DeepEval, or deterministic via `DeterministicMetric`). | `src/gavel_ai/judges/` |
| **RunContext** | Manages the lifecycle of a single evaluation run and its artifacts. | `src/gavel_ai/storage/run_context.py` |
| **ProviderFactory** | Creates Pydantic-AI agents based on model definitions. | `src/gavel_ai/providers/factory.py` |

### Data Flow

```
CLI → Config Discovery → [Executor] → [Processor] → LLM Provider → [Judge] → [RunContext] → JSONL Artifacts → [Reporter] → HTML/MD
```

### Key Architecture Decisions

- **Immutability of Raw Results:** The `results_raw.jsonl` file is never modified after execution to ensure benchmarks are stable and reproducible.
- **Provider Agnosticism:** All LLM calls must go through the `ProviderFactory` and Pydantic-AI to prevent vendor lock-in.
- **OTel-First Observability:** Every significant execution step must emit an OpenTelemetry span rather than relying solely on traditional logging.

---

## Data Models

### OutputRecord

`OutputRecord` is the unified in-pipeline type emitted by `ScenarioProcessorStep` and consumed by `JudgeRunnerStep` and `ReportRunnerStep`.

```python
class OutputRecord(BaseModel):
    scenario_id: str
    variant_id: str
    test_subject: str
    processor_output: str             # The literal LLM response
    timing_ms: float                  # Wall-clock latency
    tokens_prompt: int
    tokens_completion: int
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
```

Key invariant: records are grouped by `variant_id` in `JudgeRunnerStep` and joined by `(scenario_id, variant_id)` in `ReportRunnerStep`. `metadata` is excluded from `results_judged.jsonl` entries.

### JudgeResult

```python
class JudgeResult(BaseModel):
    score: int                        # 1-10 scaled score
    reasoning: str                    # LLM's explanation for the score
    evidence: str                     # Specific quotes or data supporting reasoning
```

### DeterministicRunResult / PerSampleDeterministicResult

New models for GT-comparison metrics (no LLM call). `DeterministicMetric` subclasses (`ClassifierMetric`, `RegressionMetric`) accumulate per-sample pairs and expose `compute()` which returns a population-level score via scikit-learn.

```python
class PerSampleDeterministicResult(BaseModel):
    scenario_id: str
    prediction: Optional[str] = None   # None when skipped before extraction
    actual: Optional[str] = None
    match: Optional[bool] = None       # ClassifierMetric only
    raw_score: Optional[float] = None  # Signed error, RegressionMetric only
    skip_reason: Optional[str] = None  # Set when sample is excluded from population metric

class DeterministicRunResult(BaseModel):
    metric_name: str
    judge_type: str                    # "classifier" or "regression"
    report_metric: str                 # scikit-learn metric name
    population_score: Optional[float]  # None if all samples skipped
    samples: List[PerSampleDeterministicResult]
```

Key invariant: deterministic results flow through `context.deterministic_metrics` → `RunData.deterministic_metrics` → `ReportData.deterministic_results`. They are **never written to `results_raw.jsonl` or `results_judged.jsonl`**.

---

## API & Interface Surface

### CLI Command Groups

```
gavel oneshot <create|run|judge|report>
gavel conv <create|run|judge|report>
gavel autotune <run|report>
gavel list
gavel diagnose
```

`gavel oneshot create` accepts:
- `--type local|in-situ` — eval type; in-situ skips prompt generation
- `--template default|classification|regression` — scaffold template; classification/regression wire deterministic judges

### External Dependencies

| Service / API | Purpose | Auth method |
|---------------|---------|-------------|
| Anthropic API | Claude models | `ANTHROPIC_API_KEY` |
| OpenAI API | GPT models | `OPENAI_API_KEY` |
| Google Vertex | Gemini models (AI Studio: `GOOGLE_API_KEY`; Vertex AI: `project`+`location`+ADC) | `GOOGLE_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` |
| Ollama | Local model execution | Instance URL (default: localhost:11434) |

---

## Implementation Conventions

### Naming

| Construct | Convention | Example |
|-----------|-----------|---------|
| Functions/Methods | `snake_case` | `run_evaluation()` |
| Classes | `PascalCase` | `RunContext` |
| JSON Fields | `snake_case` | `"variant_id"` |
| Log Levels | Standard Python | `logging.INFO` |

### Key Patterns

- **Error Handling:** Use custom exceptions from `gavel_ai.core.exceptions`. Never swallow transient API errors; use the built-in retry logic.
- **Testing:** New features MUST include unit tests in `tests/unit` and, if they touch execution, integration tests in `tests/integration`.
- **OTel Spans:** Use the `tracer` from `gavel_ai.telemetry` to wrap LLM calls and judge evaluations.
- **Step Tracking:** `Step.safe_execute()` calls `context.mark_step_complete(self.phase)` on success. `LocalRunContext` appends entries to `{run_dir}/.workflow_status` (JSONL, append-only). On init, `StepPhase.PREPARE` is written after `snapshot_run_config()`. Call `context.get_completed_steps()` to read the log.
- **Snapshot:** `LocalRunContext.snapshot_run_config()` copies `config/`, `prompts/`, and scenarios to `{run_dir}/.config/` and writes `snapshot_metadata.json`. Prompt copies land in `.config/prompts/`.
- **Judge config TOML:** Set `config_ref: "name"` on a `JudgeConfig` to load `config/judges/{name}.toml` at run time. `JudgeRunnerStep` resolves and merges TOML into `judge_config.config` before passing to `JudgeExecutor`. Use `LocalFileSystemEvalContext.get_judge_config(name)` to load directly (result is cached).
- **DeterministicMetric routing:** `JudgeRunnerStep` partitions judges by checking the class registered in `JudgeRegistry`. Types `"classifier"` and `"regression"` route to the deterministic inline loop (synchronous, no `JudgeExecutor`). All other types route to `JudgeExecutor` (LLM path). Results stored in `context.deterministic_metrics: Dict[str, DeterministicRunResult]`.
- **Score averaging exclusion:** `OneShotReporter` skips judge scores for `(scenario_id, variant_id)` pairs where `OutputRecord.error` is not None. HTML template shows `(N skipped)` annotation per variant/judge when exclusions occurred.

---

## Open Questions

- **Async Concurrency** — What are the optimal defaults for rate-limit safety across different providers? — ongoing Benchmarking

