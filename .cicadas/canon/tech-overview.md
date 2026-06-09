# Tech Overview

> Canon document. Updated by the Synthesis agent at the close of each initiative.

## What This Is

Gavel-AI is a Python-based CLI evaluation engine that follows a clean architecture pattern. It orchestrates the flow from configuration loading and scenario execution via LLM providers to automated judging and HTML/Markdown reporting. Beyond one-shot scoring, it also supports **autotune** — an automated, iterative prompt-optimization workflow that rewrites and re-judges a prompt against a scenario set until it converges.

---

## Tech Stack

| Category | Selection | Notes |
|----------|-----------|-------|
| **Language/Runtime** | Python 3.10+ | Supported versions up to 3.13. |
| **CLI Framework** | Typer | Hierarchical command structure built on Click. |
| **LLM Abstraction** | Pydantic-AI | Swappable providers (Claude, GPT, Gemini, Ollama). |
| **Evaluation/Judges** | DeepEval + scikit-learn | LLM-as-judge (11 DeepEval types including conversational) and deterministic GT-comparison metrics (accuracy, F1, MAE, etc.). |
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
│   ├── scaffolds/         # Standalone helpers for external SUT authors (no core imports)
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
| **Reporter** | Renders Jinja2 HTML/Markdown reports. `OneShotReporter._build_context()` enriches the Jinja2 context with execution time, input source, subject names, scenario count, and collapse thresholds. The OneShot template renders split LLM/deterministic judge sections, per-subject sub-headings, table-layout scenario detail with collapsible inputs and truncatable responses. `AutotuneReporter` extends `Jinja2Reporter` and renders `templates/autotune.html` (Score Progression table, Per-Judge Detail, Best Prompt Version, Run Summary — see Autotune Workflow below). | `src/gavel_ai/reporters/`, `src/gavel_ai/reporters/templates/oneshot.html`, `src/gavel_ai/reporters/templates/autotune.html` |
| **TuningAgent** | LLM-as-meta-optimizer; rewrites the prompt under test based on the prior iteration's scores and judge reasoning. Uses `ProviderFactory.create_agent()` directly — no separate LLM abstraction. | `src/gavel_ai/core/autotune/tuning_agent.py` |
| **ExternalHttpProcessor** | Sends `ExternalTaskRequest` payloads to HTTP endpoints via `httpx`; classifies HTTP 4xx/5xx and envelope-level issues into `ExternalOutcome` tiers; injects `X-Gavel-Trace-Id` header. | `src/gavel_ai/processors/external_http_processor.py` |
| **ScriptInputProcessor** | Launches subprocess scripts via `asyncio`; writes request document to a temp dir, reads response document after exit; enforces path confinement; classifies non-zero exit codes and envelope errors. | `src/gavel_ai/processors/script_processor.py` |
| **Scaffolds** | `_BaseSystemUnderTest` (abstract base), `RemoteSystemUnderTest` (HTTP), `ScriptSystemUnderTest` (subprocess + `main()` entry point); `_materialize.py` for SHA-256-headed template generation. Intentionally isolated from `gavel_ai.core.*`. | `src/gavel_ai/scaffolds/` |

### Data Flow

```
CLI → Config Discovery → [Executor] → [Processor] → LLM Provider → [Judge] → [RunContext] → JSONL Artifacts → [Reporter] → HTML/MD
```

### Key Architecture Decisions

- **Immutability of Raw Results:** The `results_raw.jsonl` file is never modified after execution to ensure benchmarks are stable and reproducible.
- **Provider Agnosticism:** All LLM calls must go through the `ProviderFactory` and Pydantic-AI to prevent vendor lock-in.
- **OTel-First Observability:** Every significant execution step must emit an OpenTelemetry span rather than relying solely on traditional logging.

---

## Autotune Workflow

`AutotuneWorkflow` (`core/workflows/autotune.py`) runs an execute → judge → rewrite loop until convergence, orchestrated as a `CompositeStep` pipeline:

```
PrepareStep (seed runs/<id>/prompts.toml v1 from config/prompts/<name>.toml)
  → ValidatorStep
  → AutotuneIterationStep (loops up to tuning.max_rounds)
        ScenarioProcessorStep → JudgeRunnerStep → [convergence check] → TuneStep
  → AutotuneReportingStep (AutotuneReporter renders templates/autotune.html)
```

### Key Architecture Decisions (ADRs — see `.cicadas/active/feat-autotune/tech-design.md` while active; archived afterward)

- **`CompositeStep` base class** (`core/steps/base.py`): owns an ordered `child_steps` list and `run_children()`, which calls each child through `safe_execute()` so inner steps get the same error-policy handling, `.workflow_status` tracking, and OTel spans as top-level steps. `AutotuneIterationStep` subclasses it, calling `run_children()` once per iteration with an `IterationRunContext`.
- **`IterationRunContext` + `IterationEvalContext`** (`core/contexts.py`): lightweight per-iteration wrappers — `IterationRunContext` redirects `results_raw`/`evaluation_results`/`run_dir` to `iterations/iteration_N/` while sharing the outer run's `eval_ctx`/`run_logger`/`run_id`; `IterationEvalContext` wraps `LocalFileSystemEvalContext` and overrides `get_prompt()` to read the current iteration's version (`vN`) from `runs/<id>/prompts.toml`, falling back to the base eval context for `v1`. Without this override, every iteration would silently re-run the original `v1` prompt — the loop would never see TuneStep's rewrites. All other `EvalContext` methods delegate unchanged via `__getattr__`.
- **`TuningAgent` uses `ProviderFactory` directly** (`core/autotune/tuning_agent.py`): same factory `PromptInputProcessor` uses, one async call per iteration — no second LLM abstraction introduced.
- **Prompt versions live in `runs/<id>/prompts.toml`, not `config/prompts/`**: keeps the eval directory immutable/read-only during runs (multiple concurrent autotune runs against the same eval don't race); `v1` is seeded by `PrepareStep` from the eval's permanent prompt, `v2+` are appended by `TuneStep`. Promoting a winning version to permanent is a manual Builder step (copy the text into `config/prompts/<name>.toml` as a new version).
- **Convergence check fires before `TuneStep`** on the iteration that triggers it — avoids a wasted TuningAgent rewrite call for a prompt version that will never be used.
- **`AutotuneReporter(Jinja2Reporter)`**: overrides `_build_context()` and renders `templates/autotune.html` with vanilla-JS score progression (no chart library dependency), matching the `OneShotReporter` subclass pattern.

### Convergence

Checked in priority order each round — first match wins and is recorded as `convergence_reason`:
`max_rounds_reached` → `target_score_achieved` → `minimal_improvement` (`|current − previous| < convergence_threshold`) → `performance_degraded` (`avg_score` drop exceeds `degradation_tolerance`).

### Score normalization (critical convention)

All `avg_score` / convergence-threshold values are normalized to a **0.0–1.0 scale**. DeepEval GEval judges return raw scores on a 0–10 scale; `AutotuneIterationStep` divides these by 10.0 before averaging. Deterministic `classifier`/`regression` judges already produce 0/1 scores and pass through unchanged. `convergence_threshold`, `target_score`, and `degradation_tolerance` in `TuningConfig` are all on this same 0.0–1.0 scale — do not confuse with the raw 1–10 `JudgeResult.score` used elsewhere.

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

### TuningConfig / IterationMetadata / AutotuneRunSummary (autotune)

```python
class TuningConfig(BaseModel):
    """EvalConfig.tuning — required when workflow_type == 'autotune'."""
    max_rounds: int                              # required, >= 1
    convergence_threshold: float = 0.02          # |current - previous| < threshold (0.0-1.0)
    target_score: Optional[float] = None         # stop early once avg_score reaches this (0.0-1.0)
    degradation_tolerance: float = 0.05          # stop if avg_score drops by more than this
    tuning_agent_model: str                      # required; key in agents.json._models
    tuning_agent_temperature: float = 0.7

class IterationMetadata(BaseModel):
    """Persisted to iterations/iteration_N/metadata.json."""
    iteration: int
    prompt_version: str                          # "v1", "v2", ...
    score: float                                  # mean normalized score (0.0-1.0)
    improvement: float                            # current_score - previous_score
    judge_scores: Dict[str, float]                # per-judge mean score breakdown
    converged: bool
    convergence_reason: Optional[str]             # one of the four convergence criteria, or null

class AutotuneRunSummary(BaseModel):
    """Persisted to runs/<id>/run_summary.json; consumed by AutotuneReporter."""
    eval_name: str
    run_id: str
    total_iterations: int
    best_iteration: int
    best_score: float
    final_score: float
    converged: bool
    convergence_reason: Optional[str]
    iterations: List[IterationMetadata]
```

`EvalConfig` gained `workflow_type: Literal["oneshot", "conversational", "autotune"]` and `tuning: Optional[TuningConfig] = None` (additive, non-breaking). `StepPhase` gained `AUTOTUNE_ITERATION` and `TUNING`.

`runs/<id>/prompts.toml` (run-local, not the eval's permanent `config/prompts/`): `[v1]` seeded from the eval's prompt at `PrepareStep`; `[v2]`, `[v3]`, ... appended by `TuneStep` with `prompt`, `iteration`, and `avg_score` (normalized 0.0-1.0) fields.

---

## API & Interface Surface

### CLI Command Groups

```
gavel init [--eval-root DIR] [--force]
gavel oneshot <create|run|judge|report|list|milestone>
gavel conv <create|generate>
gavel autotune <create|run>
```

`gavel init` initializes the project by writing `.gavel/config.json` with the chosen eval root. Idempotent; `--force` overwrites. All eval-touching commands emit a soft yellow warning to stderr if `.gavel/config.json` is absent (suppress-able by running `gavel init` first).

`gavel oneshot create` accepts:
- `--type local|in-situ` — eval type; in-situ skips prompt generation
- `--template default|classification|regression` — scaffold template; classification/regression wire deterministic judges

`gavel autotune create --eval NAME [--eval-root DIR] [--force]` scaffolds an autotune eval directory: `eval_config.json` (`workflow_type: "autotune"` + a `tuning` block), `agents.json` (registers a test-subject model and, by convention, a separate-provider judge model — see Common Mistakes), `config/prompts/<name>.toml` (v1 seed prompt), and `data/scenarios.json` pre-populated with working sample scenarios (mirrors the `oneshot create` scaffold convention so `gavel autotune run` works immediately without edits). Uses `--eval` (not a positional eval-name arg) to match the rest of the CLI's option-based pattern.

`gavel autotune run --eval NAME [--run RUN_ID] [--eval-root DIR]` executes the optimization loop; `--run` resumes a previously interrupted run by ID (continuing from the last completed iteration recorded in `.workflow_status`).

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

- **Error Handling:** Use custom exceptions from `gavel_ai.core.exceptions`. Never swallow transient API errors; use the built-in retry logic. `core/issue_classifier.py::classify(exc)` maps exceptions to three tiers: `ERROR` (HTTP 4xx/5xx, rate limits, unclassified), `WARNING` (schema/config validation failures). `EvalConfig.error_policy` (`ErrorPolicy` model) carries `exit_on_error: bool = True` and `exit_on_warning: bool = False`. `Step.safe_execute()` accepts `error_policy` and raises `RunPolicyError` immediately when a classified tier exceeds the configured threshold (fail-fast; `RunPolicyError` is never re-wrapped). `ScenarioProcessorStep` applies the same policy per-scenario using `collect_all` executor mode: error records are always written before the policy check fires.
- **Testing:** New features MUST include unit tests in `tests/unit` and, if they touch execution, integration tests in `tests/integration`.
- **OTel Spans:** Use the `tracer` from `gavel_ai.telemetry` to wrap LLM calls and judge evaluations.
- **Step Tracking:** `Step.safe_execute()` calls `context.mark_step_complete(self.phase)` on success. `LocalRunContext` appends entries to `{run_dir}/.workflow_status` (JSONL, append-only). On init, `StepPhase.PREPARE` is written after `snapshot_run_config()`. Call `context.get_completed_steps()` to read the log.
- **Snapshot:** `LocalRunContext.snapshot_run_config()` copies `config/`, `prompts/`, and scenarios to `{run_dir}/.config/` and writes `snapshot_metadata.json`. Prompt copies land in `.config/prompts/`.
- **Judge config TOML:** Set `config_ref: "name"` on a `JudgeConfig` to load `config/judges/{name}.toml` at run time. `JudgeRunnerStep` resolves and merges TOML into `judge_config.config` before passing to `JudgeExecutor`. Use `LocalFileSystemEvalContext.get_judge_config(name)` to load directly (result is cached).
- **Judge config Markdown:** Set `markdown_path: "relative/path.md"` on a `JudgeConfig` to load judge config from a Markdown file. `JudgeRunnerStep._load_markdown_judge_config()` parses `## Criteria`, `## Evaluation Steps`, `## Threshold`, and `## Guidelines` sections. Path must remain within the eval dir (path traversal rejected with `ConfigError`). Merged after `config_ref` resolution; markdown fields take precedence.
- **Judge criteria templating:** `criteria` (str) and each item in `evaluation_steps` (list) support `{{key}}` substitution. `JudgeRunnerStep._render_judge_template()` applies replacements using scenario fields (`_build_render_context()`: dict inputs unpacked, string inputs become `{"input": value}`, metadata keys merged). Unknown `{{key}}` placeholders are left unchanged.
- **Prompt templates:** Use `{{var}}` syntax in `.toml` prompt files. `ScenarioProcessorStep` validates placeholder→scenario field mapping at run-start for `local` evals and raises `ConfigError` early rather than sending literal placeholder text to the LLM. The renderer is a lightweight regex substitution — literal `{` and `}` in prompt text (JSON examples, code snippets) are passed through unchanged.
- **Token extraction:** `ProviderFactory` reads `response.usage.input_tokens` / `response.usage.output_tokens` (pydantic-ai `RunUsage` fields). `timing_ms` on `OutputRecord` is sourced from `metadata["total_latency_ms"]` (aggregated by `PromptInputProcessor`).
- **CLI error display:** Failed runs print a Rich panel to stderr with the human-readable cause and the exact path to `run.log`. Full stack traces are logged via `exc_info=True` in `Step.safe_execute()` and `OneShotWorkflow.execute()`. `OneShotWorkflow.run_ctx` is set before execution begins so the log path is always available on failure.
- **Eval root resolution:** `cli/common.py::resolve_eval_root(eval_root_str)` applies 4-tier resolution: explicit `--eval-root` CLI flag → `GAVEL_EVAL_ROOT` env var (handled by Typer `envvar=` param) → `.gavel/config.json["eval_root"]` → `.gavel/evaluations` default. All eval-touching commands accept `--eval-root` via `Annotated[Optional[str], typer.Option("--eval-root", envvar="GAVEL_EVAL_ROOT", ...)] = None` — the `None` default is critical so direct Python calls in tests receive `None`, not Typer's `OptionInfo` object.
- **Packaging (library use):** `pyproject.toml` declares `[tool.setuptools.packages.find] where = ["src"]` and `[tool.setuptools.package-data] gavel_ai = ["reporters/templates/*"]` so `pip install gavel-ai` or `uv add gavel-ai` from an external project picks up all modules and Jinja2 templates.
- **DeterministicMetric routing:** `JudgeRunnerStep` partitions judges by checking the class registered in `JudgeRegistry`. Types `"classifier"` and `"regression"` route to the deterministic inline loop (synchronous, no `JudgeExecutor`). All other types route to `JudgeExecutor` (LLM path). Results stored in `context.deterministic_metrics: Dict[str, DeterministicRunResult]`.
- **Score averaging exclusion:** `OneShotReporter` skips judge scores for `(scenario_id, variant_id)` pairs where `OutputRecord.error` is not None. HTML template shows `(N skipped)` annotation per variant/judge when exclusions occurred.
- **Scaffold convention — cross-provider judge:** `gavel oneshot create`/`conv create`/`autotune create` all register a *different*-provider model for the LLM judge than the test-subject model (e.g., test subject on `claude-haiku` / Anthropic, judge on `gpt-5-mini` / OpenAI) to avoid same-model self-evaluation bias. This means a freshly scaffolded eval needs **both** `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` set (real values, not the `{{VAR}}` placeholders) before `run` succeeds — if you only have one provider's key, edit the judge's `"model"` field in `eval_config.json` to point at a model your configured provider supports (and prune the unused `_models` entry from `agents.json`).

---

## External Runner

### Overview

`test_subject_type: "external"` delegates scenario execution (and optionally judging) to a process outside gavel's own runtime. Two transports are supported, selected by `TestSubject.protocol` (or `JudgeConfig.protocol` for external judges):

| Transport | Trigger | Wire mechanism |
|-----------|---------|----------------|
| `"http"` | `ExternalHttpProcessor` | HTTP POST via `httpx`; request body is an `ExternalTaskRequest` JSON payload; response is an `ExternalResponseEnvelope` JSON body |
| `"script"` | `ScriptInputProcessor` | `asyncio` subprocess; request written to `{tmpdir}/{request_filename}` (default `request.json`) before launch; response read from `{tmpdir}/{response_filename}` (default `response.json`) after exit |

Both transports share the same `ExternalTaskRequest` / `ExternalJudgeRequest` request models and the `ExternalResponseEnvelope` response model.

### Two-Tier Failure Model (ADR-3)

| Tier | `ExternalOutcome` enum | Meaning | Default halt behaviour |
|------|------------------------|---------|------------------------|
| Tier 1 | `PROCESS_FAILURE` | Transport-level failure: HTTP 4xx/5xx, connection error, timeout, non-zero subprocess exit, missing/invalid response document | Halt (`abort_on_exec_failure=True`) |
| Tier 2 | `PROCESS_SUCCESS_WITH_ISSUE` | Transport succeeded; response envelope carries `issue` with `status: "ok"` | Continue (`abort_on_process_error=False`) |

`classify_external_outcome(outcome, abort_on_exec_failure, abort_on_process_error, adapter)` maps outcome + policy flags to an issue tier string (`"ERROR"` / `"WARNING"`) which is stored in `ProcessorResult.metadata["external_tier"]`. The pipeline's `error_policy.should_halt(tier)` controls the actual halt decision — processors never raise for classified outcomes.

### Response Envelope

```python
ExternalResponseEnvelope:
    status: "ok" | "error"
    result: Optional[Dict[str, Any]]        # task output or judge score/reasoning
    metadata: Dict[str, Any]                # timing_ms, turns, custom fields
    issue: Optional[ExternalIssue]          # present on Tier-2 or status=error
    trace_id: Optional[str]                 # echo of inbound trace_id

ExternalIssue:
    code: str                               # stable documented code
    level: "error" | "warning"
    message: str
```

### Judge Delegation

`JudgeRunnerStep._execute_external_judge()` is invoked when `JudgeConfig.protocol` is set. It constructs an `ExternalJudgeRequest` (scenario_id, processor_output, rendered criteria, expected_behavior, custom_config, trace_id) and routes to `ExternalHttpProcessor` or `ScriptInputProcessor`. `JudgeConfig.system_id` is written as `judge_id` on the resulting `JudgedRecord`.

### Scaffolds Package

`gavel_ai.scaffolds` provides base classes for external system authors to build compliant SUT integrations. The package is intentionally isolated (no `gavel_ai.core.*` imports) so it can be installed in a separate service environment.

- `_BaseSystemUnderTest.process(raw_dict)`: full parse-validate → `handle()` → assemble lifecycle; emits structured log line with `trace_id` per invocation; wraps `handle()` exceptions into `status: "error"` envelopes automatically.
- Subclasses implement only `handle(request: ExternalTaskRequest) -> dict | ExternalIssue`.
- `ScriptSystemUnderTest.main()`: reads `request.json` from `argv[1]`, calls `process()`, writes `response.json` to `argv[2]` — entry point for subprocess scripts.
- `_materialize.py`: writes scaffold template files with a SHA-256 header so gavel can detect user modifications before overwriting.

### ADR-10 Adapter Seam

All external processors and `JudgeConfig` accept an `adapter` field (default: `"gavel"`). Only `"gavel"` is implemented in the current MVP; the field reserves a forward-compat path for plugging in custom protocol translators without schema changes.

### Schema Reference

`docs/specs/schema-external-runner.md` documents all external runner config fields, request/response schemas, and the two-tier failure model in detail.

---

## Open Questions

- **Async Concurrency** — What are the optimal defaults for rate-limit safety across different providers? — ongoing Benchmarking

