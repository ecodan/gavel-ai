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
| **Evaluation/Judges** | DeepEval | LLM-as-judge integration with GEval support. |
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
| **Judge** | Evaluates LLM output against a scenario. | `src/gavel_ai/judges/` |
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

### External Dependencies

| Service / API | Purpose | Auth method |
|---------------|---------|-------------|
| Anthropic API | Claude models | `ANTHROPIC_API_KEY` |
| OpenAI API | GPT models | `OPENAI_API_KEY` |
| Google Vertex | Gemini models | `GOOGLE_API_KEY` |
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

---

## Open Questions

- **Async Concurrency** — What are the optimal defaults for rate-limit safety across different providers? — ongoing Benchmarking

