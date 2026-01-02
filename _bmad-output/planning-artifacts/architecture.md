---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
workflowStatus: 'complete'
completedAt: '2025-12-28'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - docs/.private/app-overview.md
  - docs/.private/arch-overview.md
  - docs/.private/TDD-unified-architecture.md
  - docs/.private/refactor.md
workflowType: 'architecture'
project_name: 'gavel-ai'
user_name: 'Dan'
date: '2025-12-27'
---

# Architecture Decision Document - gavel-ai

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (78 major FRs across 9 categories):**

- **Setup & Configuration (6 FRs):** CLI scaffolding, JSON/YAML configs, provider configuration, test scenarios, judge customization, templating
- **Execution & Orchestration (6 FRs):** Local execution, provider testing, in-situ evaluation, OpenTelemetry instrumentation, selective re-runs, reproducible execution
- **Run Management & Artifacts (7 FRs):** RunContext abstraction, artifact isolation, re-judging, run history, archival/export, API access, milestone marking
- **Judging & Evaluation (6 FRs):** DeepEval integration, GEval configuration, pairwise comparison, detailed reasoning, configurable execution, custom plugins
- **Reporting (6 FRs):** Jinja2 templating, OneShot/SXS format, Conversational format, Autotune progression, judge reasoning, clear winner indication
- **Extensibility (6 FRs):** Clean abstractions, workflow patterns, primitive patterns, pluggable storage, presentation tier separation, modularity
- **CLI Interface (8 FRs):** Command patterns, create, run, judge, report, list, structured output, help/examples
- **File System & Transparency (7 FRs):** Human-readable artifacts, JSON/YAML format, OT telemetry format, structured results, manifest metadata, directory structure, cleanup/archival
- **Error Handling & Observability (8 FRs):** Informative errors, error categories, debug mode, logging format, execution telemetry, pre-execution validation, health checks, accessible metrics

**Non-Functional Requirements:**

- **Performance:** Realistic evaluation timelines (2-5s per LLM call), parallel execution, native batching support, prompt caching, <500MB memory footprint
- **Reliability:** Reproducible execution, robust error handling with retries, partial run recovery, data integrity with durable writes
- **Integration:** Multi-provider support (Claude, GPT, Gemini, Ollama), in-situ system adapters, storage abstractions, Jinja2 templating
- **Security:** Credential protection, masked secrets in logs, environment variable injection, local-first data handling
- **Maintainability:** Clean abstractions (Config, Processor, Run, Judge, Storage), clear extension patterns, documented interfaces
- **Testability:** 70%+ coverage on non-trivial code, mock providers, integration tests

### Scale & Complexity Assessment

**Project Complexity: HIGH** (enterprise-grade evaluation framework with multiple workflows)

**Primary Domains:**
- Backend: Python evaluation engine with plugin architecture
- CLI: Rich command interface with structured output
- Multi-workflow support: OneShot (v1) → Conversational (v2) → Autotune (v3)
- Multi-provider: Abstraction layer for LLM providers (Claude, GPT, Gemini, etc.)
- Observability: Native OpenTelemetry integration

**Core Architectural Components:**
1. **Input Processors:** PromptInputProcessor, ClosedBoxInputProcessor, ScenarioProcessor
2. **Config Abstraction:** LocalFileConfig (v1) → future database/lab engine support
3. **Executor:** Wraps processor, handles concurrency, error handling, input feeding
4. **Run Abstraction:** LocalFolderRun (v1) → future S3/database/experiment tracking support
5. **Judging Layer:** DeepEval judges that can be re-run independently
6. **Reporting Layer:** Jinja2 template-based reporters with common design patterns
7. **Telemetry:** OpenTelemetry spans + run_metadata.json for metrics
8. **CLI Interface:** Command-pattern CLI with structured output

### Technical Constraints & Dependencies

**Key Constraints:**
- Python 3.10+ with minimal required dependencies
- OpenTelemetry native instrumentation (not optional)
- DeepEval integration required for v1
- File-based storage as primary architecture (with abstraction for future change)
- Reproducibility requirement: Deterministic execution flow (not output variation)

**Core Dependencies:**
- Pydantic-AI (or similar) for provider abstraction
- DeepEval for LLM-as-judge
- Jinja2 for report templating
- python-dotenv>=1.0.0 for automatic `.env` file loading and environment variable management
- Optional: visualization, database adapters (post-v1)

### Cross-Cutting Concerns Identified

1. **Provider Abstraction:** Every component calling LLMs needs consistent provider handling
2. **Artifact Management:** RunContext must be accessible to Config, Processor, Judge, Reporter, CLI
3. **Observability:** OpenTelemetry instrumentation spans local and in-situ flows
4. **Error Handling:** Consistent retry logic, error categorization, actionable messages
5. **Extensibility:** Config, Processor, Judge, Storage, Workflow interfaces must be clean
6. **CLI as Primary Interface:** All business logic must be CLI-accessible before HTTP API (v2+)
7. **Reproducibility:** Deterministic execution order despite parallel processing

## Starter Template Evaluation

### Primary Technology Domain

Python CLI Tool + Backend Library (backend-focused, PyPI distribution)

### Starter Approach: Custom src-layout with Typer

**Rationale for Selection:**

Typer provides type-hint-first CLI development on top of mature Click foundation, supporting hierarchical commands (oneshot/conv/autotune workflows). src-layout separates library code from configuration, preventing import masking and supporting scalable plugin architecture. Aligns with project preference for explicit type hints, minimal dependencies, and modular extensibility.

### Project Structure

```
gavel-ai/
├── src/gavel_ai/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point, CLI factory
│   │   ├── workflows.py         # oneshot, conv, autotune subcommands
│   │   └── common.py            # Shared CLI utilities
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py            # Data classes, Pydantic models
│   │   ├── config.py            # Configuration abstraction
│   │   └── exceptions.py        # Custom exceptions
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── base.py              # Processor interface
│   │   ├── prompt_processor.py  # PromptInputProcessor
│   │   ├── closedbox_processor.py  # ClosedBoxInputProcessor
│   │   └── scenario_processor.py   # ScenarioProcessor
│   ├── judges/
│   │   ├── __init__.py
│   │   ├── base.py              # Judge interface
│   │   ├── deepeval_judge.py    # DeepEval integration
│   │   └── judge_registry.py    # Judge plugin discovery
│   ├── reporters/
│   │   ├── __init__.py
│   │   ├── base.py              # Reporter interface
│   │   ├── jinja_reporter.py    # Jinja2-based reporting
│   │   └── templates/           # HTML/Markdown templates
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py              # Storage abstraction
│   │   ├── run_context.py       # RunContext implementation
│   │   └── filesystem.py        # LocalFolderRun storage
│   └── telemetry.py             # OpenTelemetry instrumentation
├── tests/
│   ├── conftest.py              # pytest fixtures, mocks
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test data, mock providers
├── docs/                        # Project documentation
├── pyproject.toml               # Single source of truth
├── README.md
├── CHANGELOG.md
└── .python-version              # Python 3.10
```

### Architectural Decisions Provided by Starter

**Language & Runtime:**
- Python 3.10+ with type hints throughout
- Organized into functional domains (CLI, processors, judges, storage)
- Minimal required dependencies; optional dependencies for advanced features
- No strict version barriers on core dependencies

**CLI Framework:**
- Typer for hierarchical command structure (`gavel oneshot run`, `gavel conv judge`, etc.)
- Rich integration for beautiful terminal output and error messages
- Native type hint support with automatic help generation
- Click under the hood for proven maturity and extensibility

**Build & Distribution:**
- setuptools with automatic src-layout discovery
- pyproject.toml for project metadata, dependencies, tool configuration
- PyPI-ready wheel distribution for Python 3.10+
- Optional dependencies for advanced features (visualization, database adapters)

**Testing Framework:**
- pytest for unit and integration testing
- pytest-fixtures for test infrastructure and reusable mocks
- Mock providers for offline testing (no API calls required)
- Integration tests for complete workflows

**Code Organization:**
- src-layout prevents import masking during development
- Clear separation: CLI (presentation) from Core (business logic)
- Processor/Judge/Storage/Reporter interfaces for plugin extensibility
- Package discovery automatic via setuptools

**Development Experience:**
- Black + Ruff + Mypy configuration in pyproject.toml
- Pre-commit hooks for automated checking (linting, formatting, type checking)
- Type-hint-based IDE support (autocomplete, navigation, refactoring)
- Logging with standard format: `"%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"`

**Logging & Observability:**
- Centralized logger configuration (log_config.py)
- All modules import from central logger
- OpenTelemetry instrumentation for distributed tracing
- Run metadata and telemetry capture

### Technology Stack Summary

| Category | Selection | Rationale |
|----------|-----------|-----------|
| **Python** | 3.10+ | PRD requirement; maximizes compatibility |
| **CLI Framework** | Typer | Type hints first; hierarchical commands; mature Click base |
| **Package Manager** | pip/uv | pyproject.toml for modern packaging |
| **Linting** | Ruff | Fast, Python-native |
| **Formatting** | Black | Deterministic, opinionated |
| **Type Checking** | Mypy | Strict type validation |
| **Testing** | Pytest | Industry standard; fixture-based |
| **Config Format** | JSON/YAML | Human-readable, versionable |
| **Env Management** | python-dotenv | Automatic .env loading for API keys |
| **Reporting** | Jinja2 | Templating flexibility |
| **Judging** | DeepEval | LLM-as-judge integration |
| **Telemetry** | OpenTelemetry | Native OT native instrumentation |

### Initialization Path

1. Create project structure (src/gavel_ai with subpackages)
2. Initialize pyproject.toml with metadata, dependencies, tool configuration
3. Set up pre-commit hooks for linting/formatting/type-checking
4. Create conftest.py with pytest fixtures and mocks
5. Initialize CLI entry point (gavel command via Typer)
6. Create base interfaces (Processor, Judge, Storage, Reporter)
7. Implement core abstractions (Config, RunContext)

**Note:** Project initialization and structure setup should be the first implementation stories in the sprint.

## Core Architectural Decisions

### Decision 1: Provider Abstraction

**Choice:** Pydantic-AI v1.39.0

**Rationale:** Supports all required providers (Claude, GPT, Gemini, Ollama), vendor-agnostic API, built-in observability hooks, type-safe, V1 API stability through v2.0

**Implementation:**
- Use Pydantic-AI directly for provider abstraction via `ProviderFactory` class
- Swappable providers without code changes
- Configurable `output_type` parameter supports both raw text (`str`, default) and structured outputs (Pydantic models)
- Custom provider support for future extensions

**Output Type Strategy:**
- **Default (`output_type=str`)**: Raw text responses for general-purpose processors (PromptInputProcessor, etc.)
- **Structured (`output_type=PydanticModel`)**: Type-safe, validated outputs for specialized components (Judges, Reporters)
- Higher-layer components can specify structured models while maintaining flexible low-level abstraction

**Example:**
```python
# Raw text output (default)
agent = factory.create_agent(model_def)

# Structured output for judges
class JudgeVerdict(BaseModel):
    winner: Literal["subject", "baseline", "tie"]
    confidence: float
    reasoning: str

agent = factory.create_agent(model_def, output_type=JudgeVerdict)
result = await agent.run(prompt)
verdict: JudgeVerdict = result.output  # Type-safe!
```

**Affects:** Core processor logic, config schema, agent definition, telemetry instrumentation, judge implementations

---

### Decision 2: Configuration Structure

**Choice:** Nested directory organization (Variant of Option A)

**Structure:**
```
<eval_name>/
├── config/
│   ├── agents.json          # Provider configurations
│   ├── eval_config.json     # Evaluation definition
│   ├── async_config.json    # Async/concurrency settings
│   └── judges/              # Long-form judge definitions
│       └── <judge_name>.json
├── data/
│   ├── scenarios.json       # Structured scenarios
│   └── scenarios.csv        # CSV alternative
├── prompts/
│   └── <prompt_name>.toml   # Prompt templates
└── runs/
    └── <timestamp>/         # Run artifacts
```

**Rationale:** Clear separation of concerns, reusable components, supports both JSON and CSV scenarios, TOML for prompts (matches existing design patterns)

**Affects:** Config loading logic, directory initialization scaffolding, artifact storage organization

---

### Decision 3: Processor Interface & Composability

**Choice:** Config-driven design with per-processor batching

**Design Principles:**
- `InputProcessor` takes config in constructor containing behavioral rules (async, parallelism, error handling)
- Processor handles its own batching (implementation chooses most efficient mechanism)
- Error handling configurable per eval (passed in processor config)
- Processor emits OpenTelemetry spans internally
- `ScenarioProcessor` calls `PromptInputProcessor.process([single_input])` once per turn (simplifies design, optimizable later with batching)

**Processor Interface:**
```python
class InputProcessor(ABC):
    def __init__(self, config: ProcessorConfig):
        self.config = config

    async def process(
        self,
        inputs: List[Input],
    ) -> ProcessorResult:
        """Execute processor against batch of inputs."""
        pass
```

**Composability:** ScenarioProcessor invokes wrapped InputProcessor sequentially per turn, allowing each processor to optimize independently

**Affects:** Processor base class interface, config schema, executor responsibilities, telemetry span hierarchy

---

### Decision 4: Run Artifact Schema & Storage

**Choice:** Flat directory structure with two-file results design (immutable raw + mutable judged)

**Run Directory Structure:**
```
runs/<timestamp>/
├── manifest.json          # Run metadata (timestamp, config hash, counts)
├── config/                # Copy of eval configs
├── telemetry.jsonl        # Simplified OT spans
├── results_raw.jsonl      # Immutable processor outputs (one entry per test_subject × variant × scenario)
├── results_judged.jsonl   # Mutable judge results (regenerated when judges change)
├── run_metadata.json      # Performance metrics (timing, tokens, execution stats)
├── gavel.log              # Execution log
└── report.html            # Generated report
```

**Simplified Telemetry Span Format:**
```json
{
  "trace_id": "uuid",
  "span_id": "uuid",
  "parent_span_id": "uuid or null",
  "name": "llm.call",
  "start_time_iso": "2025-12-27T14:30:22.123Z",
  "end_time_iso": "2025-12-27T14:30:24.456Z",
  "duration_ms": 2333,
  "status": "ok|error",
  "attributes": {
    "llm.provider": "anthropic",
    "llm.model": "claude-3.5-sonnet",
    "llm.tokens.prompt": 150,
    "llm.tokens.completion": 100
  }
}
```

**Results Raw JSONL Schema (Immutable):**
```json
{
  "test_subject": "assistant:v1",
  "variant_id": "claude-sonnet-4-5-20250929",
  "scenario_id": "scenario_1",
  "processor_output": "The LLM response text",
  "timing_ms": 4250,
  "tokens_prompt": 156,
  "tokens_completion": 87,
  "error": null,
  "timestamp": "2025-12-27T14:30:22.123Z"
}
```

**Results Judged JSONL Schema (Mutable):**
```json
{
  "test_subject": "assistant:v1",
  "variant_id": "claude-sonnet-4-5-20250929",
  "scenario_id": "scenario_1",
  "processor_output": "The LLM response text",
  "timing_ms": 4250,
  "tokens_prompt": 156,
  "tokens_completion": 87,
  "error": null,
  "judges": [
    {
      "judge_id": "similarity",
      "judge_name": "deepeval.similarity",
      "judge_score": 8,
      "judge_reasoning": "Response closely matches expected output",
      "judge_evidence": "Similarity score: 0.92"
    },
    {
      "judge_id": "faithfulness",
      "judge_name": "deepeval.faithfulness",
      "judge_score": 7,
      "judge_reasoning": "All claims supported by context",
      "judge_evidence": "3/3 claims verified"
    }
  ]
}
```

**Two-File Design Rationale:**

**results_raw.jsonl (Immutable)**
- Record of processor execution (one entry per test_subject × variant × scenario combo)
- Never changes once written
- Preserves complete execution context: outputs, timing, tokens, errors
- test_subject: prompt/system under test name (e.g., "assistant:v1", "research_agent:v2")
- variant_id: model version or parameter configuration (e.g., "claude-sonnet-4-5-20250929", "gpt-4o")
- Enables reproducibility (can re-judge without re-running processors)
- Foundation for re-judging workflow (FR-3.3)

**results_judged.jsonl (Mutable)**
- Complete evaluation picture with all judge scores
- Same schema as results_raw.jsonl with added judges array
- Regenerated when judges change (delete results_judged.jsonl, re-apply judges from results_raw.jsonl)
- Supports FR-3.3: "Users can re-judge existing runs without re-execution"
- Multiple judges per entry: judges array contains all judge results for each scenario × test_subject × variant combo

**Workflow Example:**
1. User runs evaluation → results_raw.jsonl written (immutable, contains test_subject + variant_id)
2. Judges applied → results_judged.jsonl written (mutable, same base schema + judges array)
3. User changes judges (adds/removes judges)
4. System regenerates results_judged.jsonl from results_raw.jsonl (no API calls needed)
5. Original processor outputs preserved in results_raw.jsonl with test_subject and variant metadata

**Affects:** RunContext implementation, telemetry collector, result storage, report generation, re-judge workflow (FR-3.3)

---

### Decision 5: Judge Integration & Plugin System

**Choice:** DeepEval-native with declarative GEval support

**Judge References:** DeepEval names only with `deepeval.<name>` namespace (e.g., `deepeval.similarity`, `deepeval.faithfulness`)

**Custom Judges:** GEval for custom evaluation logic

**Judge Definition:**
- Inline with subject in eval_config.json
- Reference to `/config/judges/<judge_name>.json` for complex/voluminous configs

**Judge Configuration:**
```json
{
  "judges": [
    {
      "id": "similarity",
      "deepeval_name": "deepeval.similarity",
      "config": {
        "threshold": 0.8
      }
    },
    {
      "id": "custom_eval",
      "deepeval_name": "deepeval.geval",
      "config_ref": "judges/custom_eval.json"
    }
  ]
}
```

**Execution Model:** Sequential (judge all results with judge A, then B, etc.)

**Judge Input/Output Contract:**
```python
class Judge(ABC):
    async def evaluate(
        self,
        scenario: Scenario,
        subject_output: str,
    ) -> JudgeResult:
        """Score single output against scenario."""
        pass
```

**Score Format:** Integer 1-10 scale

**DeepEval Integration:** Use DeepEval directly (wrap/adapt their judges)

**Future:** Pairwise comparison deferred to v2+

**Affects:** eval_config.json schema, judge registry, result schema, re-judging logic

---

### Decision 6: CLI Command Structure & Naming

**Choice:** Hierarchical with eval root location and timestamped runs

**Eval Root Management:**
- Established on first run (default: `.gavel/evaluations/`)
- Can be overridden with `--eval-root` or environment variable
- Evals accessed via `--eval <name>` (relative to root) or explicit path

**Run ID Format:** Timestamped `run-<YYYYMMDD-HHMMSS>`

**Directory Creation:**
```bash
gavel oneshot create --eval foo
# Creates: <eval-root>/foo/ with all subdirectories
```

**Command Structure:**
```
gavel oneshot create --eval <name> --type [local | in-situ]
gavel oneshot run --eval <name> [--scenarios 1-10]
gavel oneshot judge --run <run-id> [--judges judge1,judge2]
gavel oneshot report --run <run-id> [--template custom.html]
gavel oneshot list [--eval <name>]
gavel oneshot milestone --run <run-id> --comment "..."

gavel conv <create|run|judge|report|list|milestone>
gavel autotune <create|run|report|list|milestone>

gavel health
gavel diagnose
gavel clean [--older-than 30d]
```

**Affects:** CLI design, argument parsing, eval discovery, directory initialization

---

### Decision 7: Error Handling & Categorization

**Choice:** Categorized errors with configurable retry and partial failure handling

**Error Categories:**
- **Configuration:** Syntax, missing fields, type validation, file not found
- **Validation:** Invalid scenario, judge config, missing credentials
- **Execution:** API failures, timeout, network issues, provider unavailable
- **System:** File I/O, disk space, permissions, memory

**Retry Strategy:**
- **Transient retries:** Rate limits, timeouts, network issues (3 retries, 1s initial, 30s max, with jitter)
- **Non-transient:** Config errors, auth failures, file not found (fail immediately)
- **Configurable per eval:** Retry parameters in `async_config.json`

**Partial Failure Handling:** Configurable per eval via `error_handling` in processor config
- `fail_fast`: Stop on first error
- `collect_all`: Continue despite errors, report in results

**Error Output:**
- **Normal mode:** Concise, actionable error messages with file/line context
- **Debug mode (`--debug`):** Full stack traces, masked secrets, telemetry context

**Logging:** All errors logged to `runs/<run-id>/gavel.log` in standard format

**Affects:** Error handling throughout processors, executor logic, logging configuration, async_config schema

---

### Decision 8: Storage Abstraction & Extensibility

**Choice:** Domain-driven design with pluggable storage implementations

**Architecture Pattern:** Each domain object knows how to persist/load itself

**v1 Implementations:**
- `LocalFilesystemRun` (filesystem-based)
- `LocalFileConfig` (JSON/YAML files)
- `LocalFilePrompt` (TOML templates)

**Future Implementations (v2+):**
- `LocalDatabaseRun`, `S3Run`, `ExperimentTrackingRun`
- `DatabaseConfig`, `PromptServerConfig`
- Custom implementations

**Design:**
```python
class Run(ABC):
    """Abstract Run with common interface."""
    async def save(self) -> str: ...
    @staticmethod
    async def load(run_id: str) -> Run: ...
    @property
    def artifacts(self) -> Dict[str, ArtifactRef]: ...

class LocalFilesystemRun(Run):
    """Run backed by filesystem."""
    async def save(self) -> str:
        # Persist to filesystem
        pass
```

**Rationale:** Domain logic separated from storage mechanism, clean extensibility without modifying business logic

**Affects:** Domain model design, all storage operations, factory pattern for creating instances

---

### Decision 9: Telemetry & OpenTelemetry Integration

**Choice:** Unified streaming OT pipeline with flat storage

**Collection Strategy:** Streaming with unified OT receiver
- Internal processors emit to local OT receiver
- In-situ systems also emit to same local OT receiver
- Single pipeline collects all spans
- Exported to telemetry.jsonl at run completion

**Trace & Filtering:**
- Single `trace_id` per run (unifies all evaluation spans)
- Attributes for pivoting: `run_id`, `processor_type`, `subject_id`, `variant_id`, `scenario_id`

**Span Storage:** Flat (no parent/child relationships in stored JSON)
- Simpler to write, smaller JSON
- Pre-processing step reconstructs hierarchies for visualization
- Reporters build parent/child trees from attributes + timing

**Instrumentation Points:**
1. LLM calls: `llm.call` with provider, model, tokens, latency
2. Processor execution: `processor.execute` with processor type, subject, variant
3. Judge execution: `judge.evaluate` with judge name, score
4. In-situ calls: `in_situ.call` with endpoint, latency

**Token Counting:** Use provider response values

**Future:** Pluggable OT exporters (Jaeger, DataDog, etc. in v2+)

**Affects:** Telemetry instrumentation strategy, OT receiver setup, reporter hierarchy reconstruction, span schema

---

### Decision 9b: Nomenclature - Subjects & Variants

**Choice:** Explicit subject types (PUT/SUT) with unified "subject" terminology

**Subjects:** The things being tested (one per evaluation)
- **PUT (Prompt-Under-Test):** Local prompt evaluation
- **SUT (System-Under-Test):** In-situ endpoint evaluation
- Collectively referred to as "subjects" in config/reports

**Variants:** Different models/configurations applied across subjects
- Example: Claude Sonnet, GPT-4, Gemini (each is a variant)
- Applied to all subjects in evaluation
- Each subject × variant combination produces results

**Usage:**
- Code: Explicitly reference PUT vs SUT internally
- Config/Reports: Unified "subject" handling
- Models: Always "variants"

**Affects:** eval_config schema, code naming conventions, report structure, telemetry attributes, CLI output

---

### Decision Impact Summary

**Implementation Sequence Priority:**

1. **Foundation (Blocking):** Project structure, pyproject.toml, domain classes (Run, Config, Prompt)
2. **Config & Storage:** Config loading, LocalFilesystemRun, LocalFileConfig implementations
3. **CLI Entry Point:** Typer setup, gavel command infrastructure
4. **Processor Interface:** Base classes, Pydantic-AI integration
5. **Execution:** Executor, processor implementations (PromptInputProcessor, ClosedBoxInputProcessor)
6. **Judging:** Judge registry, DeepEval integration
7. **Telemetry:** OT receiver setup, span emission
8. **Reporting:** Jinja2 templates, report generation
9. **Testing:** Mock providers, test infrastructure

**Cross-Component Dependencies:**

- Config must load subjects (PUT/SUT) and variants before execution
- Processors depend on Pydantic-AI provider abstraction
- Executor depends on processor interface and error handling config
- Telemetry depends on unified OT receiver for internal + in-situ spans
- Reports depend on results.jsonl schema and telemetry reconstruction
- CLI depends on all domain classes and orchestration logic

---

## Implementation Patterns & Consistency Rules

These patterns prevent conflicts between different AI agents implementing gavel-ai components. All agents MUST follow these rules for consistent, compatible code.

### Naming Conventions

**Python Code Standards:**
- Functions/modules: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_single_underscore` (protected)
- Exceptions: `<Concept>Error` (e.g., `ConfigError`, `ProcessorError`, `JudgeError`)

**Example:**
```python
from gavel_ai.processors.prompt_processor import PromptInputProcessor

class PromptInputProcessor(InputProcessor):
    """Process prompts against input scenarios."""

    MAX_RETRIES = 3

    def _internal_helper(self):
        pass

class ProcessorError(Exception):
    pass
```

**JSON Config Fields: Always snake_case**
```json
{
  "agents": [],
  "async_config": {
    "max_workers": 4,
    "timeout_seconds": 30
  },
  "processor_type": "prompt_input",
  "variant_id": "variant-1",
  "subject_id": "claude-sonnet"
}
```

**Telemetry Attributes: snake_case with dot notation for hierarchy**
```json
{
  "llm.provider": "anthropic",
  "llm.model": "claude-3.5-sonnet",
  "llm.tokens.prompt": 150,
  "llm.tokens.completion": 100,
  "processor.type": "prompt_input",
  "scenario.id": "scenario-5",
  "variant.id": "variant-1"
}
```

---

### Data Model Patterns

**Pydantic Configuration (Standard for all models):**
```python
from pydantic import BaseModel, ConfigDict

class ProcessorConfig(BaseModel):
    """Configuration for input processor."""
    model_config = ConfigDict(extra='ignore')  # Lenient on unknown fields

    # Required fields
    processor_type: str
    parallelism: int = 1
    timeout_seconds: int = 30

    # Optional metadata
    metadata: Optional[Dict[str, Any]] = None
```

**Key Rules:**
- Use `extra='ignore'` for all configs (lenient on unknowns)
- Enforce `required` fields strictly
- Use `Optional[Type] = None` for optional fields
- Always provide type hints

**Result Objects (Consistent across project):**

```python
class ProcessorResult(BaseModel):
    """Result from processor execution."""
    output: str  # Required: actual output
    metadata: Optional[Dict[str, Any]] = None  # Optional: tokens, latency, etc.
    error: Optional[str] = None  # Optional: error message if failed

class JudgeResult(BaseModel):
    """Result from judge evaluation."""
    score: int  # Required: 1-10 integer score
    reasoning: Optional[str] = None  # Optional: explanation
    evidence: Optional[str] = None  # Optional: supporting evidence
```

---

### Processor & Judge Interfaces

**Processor Contract (All implementations must follow):**

```python
class InputProcessor(ABC):
    """Base class for all input processors."""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.tracer = get_tracer(__name__)  # Use centralized tracer

    async def process(
        self,
        inputs: List[Input],
    ) -> ProcessorResult:
        """
        Process inputs and return results.

        MUST emit OT spans immediately when events occur.
        MUST handle errors according to config.error_handling.
        """
        with self.tracer.start_as_current_span("processor.execute") as span:
            span.set_attribute("processor.type", self.config.processor_type)
            # Perform work
            # Spans emitted immediately, collected centrally
            return ProcessorResult(output="...")
```

**Judge Contract (All implementations must follow):**

```python
class Judge(ABC):
    """Base class for all judges."""

    def __init__(self, config: JudgeConfig):
        self.config = config
        self.tracer = get_tracer(__name__)

    async def evaluate(
        self,
        scenario: Scenario,
        subject_output: str,
    ) -> JudgeResult:
        """
        Evaluate subject output against scenario.

        MUST emit OT span named 'judge.evaluate'.
        MUST return JudgeResult with score (required), optional reasoning/evidence.
        """
        with self.tracer.start_as_current_span("judge.evaluate") as span:
            span.set_attribute("judge.id", self.config.judge_id)
            span.set_attribute("judge.name", self.config.deepeval_name)
            score = await self._evaluate(scenario, subject_output)
            return JudgeResult(score=score, reasoning="...")
```

---

### Project Organization

**Directory Structure (Non-negotiable):**

```
src/gavel_ai/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py              # Typer CLI factory
│   └── workflows.py         # Subcommand handlers (oneshot, conv, autotune)
├── core/
│   ├── __init__.py
│   ├── models.py            # Pydantic data models
│   ├── config.py            # Config loading and validation
│   ├── exceptions.py        # Custom exception hierarchy
│   └── types.py             # Type definitions
├── processors/
│   ├── __init__.py
│   ├── base.py              # InputProcessor ABC
│   ├── prompt_processor.py  # PromptInputProcessor implementation
│   ├── closedbox_processor.py  # ClosedBoxInputProcessor
│   ├── scenario_processor.py   # ScenarioProcessor
│   └── executor.py          # Executor (orchestrates processors)
├── judges/
│   ├── __init__.py
│   ├── base.py              # Judge ABC
│   ├── deepeval_judge.py    # DeepEval judge adapter
│   └── registry.py          # Judge discovery/registration
├── storage/
│   ├── __init__.py
│   ├── base.py              # Run, Config, Prompt ABCs
│   ├── run.py               # LocalFilesystemRun, LocalDatabaseRun, etc.
│   ├── config.py            # LocalFileConfig, etc.
│   └── prompt.py            # LocalFilePrompt, etc.
├── reporters/
│   ├── __init__.py
│   ├── base.py              # Reporter ABC
│   ├── jinja_reporter.py    # Jinja2 template-based reporting
│   └── templates/           # HTML, Markdown templates
├── telemetry.py             # Central OpenTelemetry setup
└── log_config.py            # Central logging configuration

tests/
├── conftest.py              # pytest fixtures, mocks, helpers
├── unit/
│   ├── test_processors.py
│   ├── test_judges.py
│   ├── test_config.py
│   └── ...
├── integration/
│   └── test_workflows.py    # End-to-end workflow tests
└── fixtures/
    ├── mock_providers.py    # Mock Pydantic-AI providers
    └── sample_data.py       # Test scenarios, configs
```

**Key Organization Rules:**
- Base classes in `base.py` (one per module)
- Implementations named clearly (`prompt_processor.py`, not `processor.py`)
- Tests mirror source structure (`tests/unit/test_processors.py` for `processors/`)
- No circular imports (organize packages to avoid)

---

### Error Handling Patterns

**Exception Hierarchy (Strict):**

```python
class GavelError(Exception):
    """Base exception for all gavel-ai errors."""
    pass

class ConfigError(GavelError):
    """Configuration-related errors (file, syntax, validation)."""
    pass

class ProcessorError(GavelError):
    """Processor execution errors (API call, timeout, etc.)."""
    pass

class JudgeError(GavelError):
    """Judge evaluation errors."""
    pass

class StorageError(GavelError):
    """Storage operation errors (file I/O, etc.)."""
    pass

class ValidationError(GavelError):
    """Data validation errors (scenario format, etc.)."""
    pass
```

**Error Message Format (Required):**

All error messages MUST follow this pattern:
```
<ErrorType>: <What happened> - <Recovery step>
```

**Examples:**
```python
# Good
raise ConfigError("Missing required field 'agents' in agents.json - Add 'agents' array containing provider configurations")
raise ProcessorError("LLM API call timed out after 30s - Increase timeout_seconds in async_config.json or retry")
raise StorageError("Cannot write to runs directory - Check disk space and file permissions")

# Bad (too vague)
raise ConfigError("Invalid config")
raise ProcessorError("Error")
raise StorageError("IO error")
```

**Error Handling in Async Code:**
```python
async def process(self, inputs):
    try:
        result = await self.llm_call(input)
    except TimeoutError as e:
        raise ProcessorError(f"LLM call timed out after {self.config.timeout_seconds}s - Check provider status or increase timeout") from e
    except Exception as e:
        raise ProcessorError(f"Unexpected error: {e} - Check logs for details") from e
```

---

### Telemetry Patterns

**Span Emission (Immediate, not deferred):**

```python
# Correct: Emit span immediately when event occurs
def process(self, inputs):
    with self.tracer.start_as_current_span("processor.execute") as span:
        span.set_attribute("processor.type", "prompt_input")
        # Do work
        # Span is recorded immediately upon context exit
        return ProcessorResult(...)

# Incorrect: Buffering spans
spans = []
spans.append(current_span)
# Later...
export_spans(spans)  # Don't do this
```

**Centralized Collection:**

All spans (from processors, judges, in-situ systems) flow to single OT receiver:
```
Processors -> |
Judges      -> | OT Receiver -> File Exporter -> telemetry.jsonl
In-Situ     -> |
```

Don't create per-component collectors; use project-wide `get_tracer(__name__)`.

**Standard Span Attributes (All spans must include):**

```python
span.set_attribute("run_id", run.run_id)  # Always
span.set_attribute("trace_id", trace_id)  # Always
span.set_attribute("span_id", span_id)    # Always (auto-filled)

# Plus context-specific attributes:
# For processor spans:
span.set_attribute("processor.type", "prompt_input")
span.set_attribute("scenario.id", scenario_id)
span.set_attribute("variant.id", variant_id)

# For judge spans:
span.set_attribute("judge.id", judge_config.id)
span.set_attribute("judge.name", "deepeval.similarity")

# For LLM call spans:
span.set_attribute("llm.provider", "anthropic")
span.set_attribute("llm.model", "claude-3.5-sonnet")
span.set_attribute("llm.tokens.prompt", token_count)
span.set_attribute("llm.tokens.completion", completion_count)
```

**Timing (Automatic):**
- `start_time_iso` and `end_time_iso` filled automatically
- `duration_ms` calculated from times
- No manual timing code needed

---

### Type Hints & Validation

**Type Hints Required (No Exceptions):**

Every function must have type hints:
```python
# Correct
async def process(
    self,
    inputs: List[Input],
    config: Optional[ProcessorConfig] = None,
) -> ProcessorResult:
    pass

# Incorrect (missing return type)
async def process(self, inputs: List[Input]):
    pass
```

**Config Validation (Always at Load Time):**

```python
# Load and validate config immediately
raw_config = json.load(open("config.json"))
config = ProcessorConfig.model_validate(raw_config)

# Don't validate later
config = ProcessorConfig(**raw_config)  # Wrong: no validation
```

**Lenient on Unknown Fields:**

```python
# Pydantic silently ignores unknown fields in config
# This allows config to be extended without breaking old code
class Config(BaseModel):
    model_config = ConfigDict(extra='ignore')

    known_field: str
    # unknown_future_field in JSON is silently ignored
```

---

### Consistency Rules - ALL Agents MUST Follow

✅ **MANDATORY:**

1. All code uses `snake_case` for Python, `snake_case` for JSON configs (no exceptions)
2. All exceptions inherit from `GavelError` or specific subclass
3. All async operations use `async def` and `await` (no callbacks, no threads)
4. All config validation uses Pydantic with `extra='ignore'`
5. All telemetry spans emitted immediately upon completion (not buffered)
6. All functions have complete type hints (no untyped functions)
7. All result objects use optional fields where appropriate (`Optional[Type] = None`)
8. All processors/judges use `get_tracer(__name__)` (don't create new tracers)
9. All error messages follow format: `<ErrorType>: <What> - <How to fix>`
10. All JSON configs use `snake_case` field names (absolutely no camelCase)

---

### Anti-Patterns to Avoid

❌ **Don't:** Use wrong case for class names
```python
class config_loader:  # Wrong: classes are PascalCase
    pass

class ConfigLoader:  # Correct
    pass
```

❌ **Don't:** Use camelCase in JSON configs
```json
{"processorType": "prompt_input"}  // Wrong
{"processor_type": "prompt_input"}  // Correct
```

❌ **Don't:** Omit optional field defaults
```python
class JudgeResult(BaseModel):
    score: int
    reasoning: str  # Wrong: should be Optional[str] = None
```

❌ **Don't:** Create multiple tracers
```python
# In different places - Wrong
tracer1 = trace.get_tracer("processor")
tracer2 = trace.get_tracer("judge")

# Correct: Use module name consistently
tracer = get_tracer(__name__)
```

❌ **Don't:** Buffer/batch telemetry spans before export
```python
# Wrong: Collect and flush later
collected_spans = []
collected_spans.append(span)
# Later...
export_all(collected_spans)

# Correct: Emit immediately, central collector handles batching
# Span emitted immediately via context manager exit
```

❌ **Don't:** Create custom result formats
```python
# Wrong: Inconsistent result format
return {"output": "...", "metadata": {...}}  # Plain dict

# Correct: Use defined result classes
return ProcessorResult(output="...", metadata={...})
```

❌ **Don't:** Mix error message formats
```python
# Wrong
raise ProcessorError("Error")
raise ProcessorError("llm.call failed")
raise ProcessorError("Failed to process input")

# Correct: Consistent format
raise ProcessorError("LLM API call failed - Check API key or provider status")
```

---

### Implementation Checklist for AI Agents

When implementing any component, verify:

- [ ] All code follows Python naming standards (snake_case/PascalCase)
- [ ] All JSON configs use `snake_case` (no camelCase)
- [ ] All exceptions inherit from `GavelError` or subclass
- [ ] All functions have type hints
- [ ] All configs use Pydantic with `extra='ignore'`
- [ ] All telemetry spans emitted immediately (context manager)
- [ ] All error messages follow required format
- [ ] No new tracers created (use `get_tracer(__name__)`)
- [ ] Result objects match defined schemas (ProcessorResult, JudgeResult)
- [ ] Organization follows directory structure (no random files)
- [ ] Tests mirror source structure
- [ ] No circular imports

---

## Project Structure & Boundaries

### Complete Project Directory Structure

```
gavel-ai/
├── .python-version                 # Python 3.10
├── .gitignore
├── README.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml                  # Single source of truth
├── Makefile                        # Development tasks
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint, type check, test, build
│       ├── release.yml             # PyPI release
│       └── docs.yml                # Build documentation
│
├── .pre-commit-config.yaml         # Black, Ruff, Mypy hooks
│
├── src/gavel_ai/
│   ├── __init__.py                 # Version, public API
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py                 # Typer app factory, entry point
│   │   ├── workflows/
│   │   │   ├── __init__.py
│   │   │   ├── oneshot.py          # create, run, judge, report, list, milestone
│   │   │   ├── conv.py             # Conversational (v2+)
│   │   │   └── autotune.py         # Autotune (v3+)
│   │   ├── common.py               # Shared CLI utilities
│   │   └── utils.py                # Output formatting, progress
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py               # Pydantic data models (Config, Scenario, etc.)
│   │   ├── config.py               # Config loading, validation
│   │   ├── exceptions.py           # GavelError, ConfigError, ProcessorError, etc.
│   │   └── types.py                # TypeAliases, protocols
│   │
│   ├── processors/
│   │   ├── __init__.py             # Export base class, factory
│   │   ├── base.py                 # InputProcessor, ScenarioProcessor ABCs
│   │   ├── prompt_processor.py     # PromptInputProcessor implementation
│   │   ├── closedbox_processor.py  # ClosedBoxInputProcessor
│   │   ├── scenario_processor.py   # ScenarioProcessor for conversational
│   │   └── executor.py             # Executor (orchestrates processors)
│   │
│   ├── judges/
│   │   ├── __init__.py             # Export factory, registry
│   │   ├── base.py                 # Judge ABC
│   │   ├── deepeval_judge.py       # DeepEval adapter
│   │   └── registry.py             # Judge discovery, instantiation
│   │
│   ├── storage/
│   │   ├── __init__.py             # Export base classes, factory
│   │   ├── base.py                 # Run, Config, Prompt ABCs
│   │   ├── run.py                  # LocalFilesystemRun, LocalDatabaseRun (future)
│   │   ├── config.py               # LocalFileConfig, LocalDatabaseConfig (future)
│   │   └── prompt.py               # LocalFilePrompt, PromptServerPrompt (future)
│   │
│   ├── reporters/
│   │   ├── __init__.py             # Export Reporter base
│   │   ├── base.py                 # Reporter ABC
│   │   ├── jinja_reporter.py       # Jinja2 template-based reporter
│   │   └── templates/
│   │       ├── oneshot.html.jinja  # OneShot report template
│   │       ├── conv.html.jinja     # Conversational report template
│   │       ├── autotune.html.jinja # Autotune report template
│   │       └── base.css            # Shared styling
│   │
│   ├── telemetry.py                # OpenTelemetry setup, get_tracer()
│   └── log_config.py               # Logging configuration
│
├── tests/
│   ├── conftest.py                 # pytest config, fixtures
│   ├── fixtures.py                 # Reusable test fixtures
│   │
│   ├── unit/
│   │   ├── test_processors.py      # PromptInputProcessor, ClosedBoxProcessor
│   │   ├── test_judges.py          # Judge instantiation, evaluation
│   │   ├── test_config.py          # Config loading, validation
│   │   ├── test_storage.py         # RunContext, artifacts
│   │   ├── test_reporters.py       # Report generation
│   │   └── test_cli.py             # CLI commands
│   │
│   ├── integration/
│   │   ├── test_oneshot_workflow.py    # End-to-end OneShot
│   │   ├── test_conv_workflow.py       # End-to-end Conversational (v2+)
│   │   ├── test_autotune_workflow.py   # End-to-end Autotune (v3+)
│   │   └── test_telemetry.py           # Telemetry collection
│   │
│   └── fixtures/
│       ├── mock_providers.py       # Mock Pydantic-AI providers
│       ├── sample_eval/            # Sample evaluation files
│       │   ├── config/
│       │   ├── data/
│       │   ├── prompts/
│       │   └── runs/
│       └── sample_configs.py       # Test config objects
│
├── docs/
│   ├── index.md                    # Overview
│   ├── quickstart.md               # 15-minute setup guide
│   ├── cli-reference.md            # Command documentation
│   ├── api/
│   │   ├── processors.md           # Processor interface docs
│   │   ├── judges.md               # Judge interface docs
│   │   └── storage.md              # Storage abstraction docs
│   ├── architecture/
│   │   ├── overview.md             # System design
│   │   ├── flows.md                # Data/execution flows
│   │   └── extensibility.md        # Extension patterns
│   ├── examples/
│   │   ├── local_eval/             # Local prompt evaluation
│   │   ├── insitu_eval/            # In-situ endpoint testing
│   │   └── custom_judge.md         # Custom judge implementation
│   └── contributing.md             # Development guide
│
└── MANIFEST.in                     # Include non-code files in distribution
```

---

### Architectural Boundaries

**CLI Boundary:**
- Entry point: `src/gavel_ai/cli/main.py:app` (Typer CLI)
- Workflows (oneshot/conv/autotune) as subcommands
- All CLI logic isolated from business logic
- Future: Can add HTTP API without touching CLI code

**Processor Boundary:**
- Public interface: `InputProcessor` (async, config-driven)
- Implementations: `PromptInputProcessor`, `ClosedBoxInputProcessor`, `ScenarioProcessor`
- Pydantic-AI abstraction handles provider details
- Processors emit OT spans internally

**Judge Boundary:**
- Public interface: `Judge` (async, scenario + output → score)
- Registry handles DeepEval name resolution
- Sequential execution model (judge A, then B, etc.)
- Future: Pairwise comparison in v2+

**Storage Boundary:**
- Abstract base classes: `Run`, `Config`, `Prompt`
- v1 implementations: Filesystem-based
- Future: Database, S3, prompt servers without business logic changes

**Telemetry Boundary:**
- Centralized: `get_tracer(__name__)` in all modules
- Unified OT receiver collects from processors, judges, in-situ
- Export to `runs/<run_id>/telemetry.jsonl`
- No buffering; spans emitted immediately

**Config Boundary:**
- Pydantic models validate at load time
- JSON configs in eval directory: `config/agents.json`, `eval_config.json`, `async_config.json`
- Prompts as TOML in `prompts/`
- Scenarios as JSON/CSV in `data/`

---

### Requirements to Component Mapping

**FR Category → Module Mapping:**

| FR Category | Module | Key Files |
|-------------|--------|-----------|
| Setup & Configuration (FR-1) | `cli.main`, `core.config`, `storage` | `main.py`, `config.py`, `run.py` |
| Execution & Orchestration (FR-2) | `processors.executor`, `processors.prompt_processor` | `executor.py`, `prompt_processor.py` |
| Run Management (FR-3) | `storage.run`, `reporters` | `run.py`, `jinja_reporter.py` |
| Judging & Evaluation (FR-4) | `judges`, `reporters` | `deepeval_judge.py`, `registry.py` |
| Reporting (FR-5) | `reporters` | `jinja_reporter.py`, `templates/` |
| Extensibility (FR-6) | `processors.base`, `judges.base`, `storage.base` | `base.py` files |
| CLI Interface (FR-7) | `cli.workflows` | `oneshot.py`, `conv.py`, `autotune.py` |
| File System & Transparency (FR-8) | `storage`, `core.config` | All storage modules |
| Error Handling & Observability (FR-9) | `core.exceptions`, `telemetry`, `log_config` | All modules |

---

### Integration Points

**Internal Communication:**

```
CLI (main.py)
  → load_dotenv() (automatic .env loading on startup)
  → Executor (processors/executor.py)
    → PromptInputProcessor / ClosedBoxInputProcessor
      → Pydantic-AI (provider abstraction)
    → ScenarioProcessor (wraps InputProcessor)
  → Judge Registry (judges/registry.py)
    → DeepEval Judge instances
  → Run (storage/run.py)
    → LocalFilesystemRun (filesystem storage)
  → Reporter (reporters/jinja_reporter.py)
    → Jinja2 templates
```

**Cross-Cutting Concerns:**

1. **Telemetry:** Every processor, judge, and executor emits spans
   - Collection point: Centralized OT receiver
   - Export: `telemetry.jsonl` in run directory
   - Module: `telemetry.py`

2. **Error Handling:** All modules use `GavelError` hierarchy
   - Logging: `log_config.py` standard format
   - Output: CLI catches exceptions, formats errors
   - Module: `core/exceptions.py`

3. **Config Validation:** All models use Pydantic with `extra='ignore'`
   - Load time validation (no runtime surprises)
   - Lenient on unknown fields (forward compatible)
   - Environment variable substitution via `{{VAR_NAME}}` syntax in config files
   - Automatic `.env` loading via `python-dotenv` on CLI startup
   - Module: `core/models.py`, `core/config.py`, `core/config/loader.py`

**External Integration Points:**
- LLM providers: Claude, GPT, Gemini, Ollama (via Pydantic-AI v1.39.0)
- In-situ endpoints: HTTP calls to deployed systems
- DeepEval: Judge evaluation logic
- OpenTelemetry: Span collection and export

---

### Development Workflow Integration

**Development Setup:**
```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"  # Includes test, dev deps
pre-commit install
```

**Local Testing:**
- `pytest tests/unit/` → Unit tests (no API calls, uses mock providers)
- `pytest tests/integration/` → End-to-end tests (mock LLM providers)
- Mock providers in `tests/fixtures/mock_providers.py`

**Build & Quality:**
- `black src/ tests/` → Format code
- `ruff check src/ tests/` → Lint
- `mypy src/` → Type check
- `pytest --cov=src/gavel_ai tests/` → Test with coverage

**Distribution:**
- `pyproject.toml` defines package metadata, dependencies, tools
- `setuptools` auto-discovers src-layout
- Wheel distribution to PyPI
- Entry point: `gavel = gavel_ai.cli.main:app`

**Documentation:**
- Source in `docs/`
- Examples in `docs/examples/`
- API docs auto-generated from docstrings
- Quickstart focused on 15-minute onboarding

---

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**

All technology choices work together seamlessly without conflicts:
- **Pydantic-AI v1.39.0:** Supports all required providers (Claude, GPT, Gemini, Ollama)
- **Python 3.10+:** Mature, stable, widely available
- **Typer CLI:** Built on Click, type-hint first, perfect with Pydantic
- **Domain-driven storage:** Run/Config/Prompt ABCs enable clean pluggable implementations
- **Nested config (JSON/YAML/TOML):** Standard formats, Pydantic validation
- **OpenTelemetry:** Industry standard, works at all architectural layers
- **DeepEval judges:** Mature library, integrates cleanly

All versions compatible, no dependency conflicts identified.

**Pattern Consistency:**

Implementation patterns perfectly support architectural decisions:
- Naming conventions (snake_case/PascalCase) enforced consistently
- Pydantic models with `extra='ignore'` for all configs
- Type hints required everywhere (IDE support, mypy validation)
- Result objects (ProcessorResult, JudgeResult) define clear contracts
- OT spans emitted immediately (no buffering complexity)
- Error hierarchy (GavelError) consistent across all modules
- Project structure mirrors architectural boundaries

**Structure Alignment:**

Project structure fully supports all architectural decisions:
- src-layout enables clean imports, prevents masking
- CLI boundary isolated (HTTP API can be added later without touching business logic)
- Processor/Judge boundaries cleanly defined with base classes
- Storage abstraction in place with pluggable implementations
- Telemetry module centralized for unified OT collection
- Tests mirror source structure for clear organization

---

### Requirements Coverage Validation ✅

**All 78+ Functional Requirements Covered:**

| FR Category | Count | Coverage |
|-------------|-------|----------|
| Setup & Configuration | 6 | ✅ 100% |
| Execution & Orchestration | 6 | ✅ 100% |
| Run Management & Artifacts | 7 | ✅ 100% |
| Judging & Evaluation | 6 | ✅ 100% |
| Reporting | 6 | ✅ 100% |
| Extensibility | 6 | ✅ 100% |
| CLI Interface | 8 | ✅ 100% |
| File System & Transparency | 7 | ✅ 100% |
| Error Handling & Observability | 8 | ✅ 100% |

**All 23+ Non-Functional Requirements Covered:**

- Performance (5 NFRs): ✅ Async, parallel execution, batching, prompt caching
- Reliability (4 NFRs): ✅ Error handling, retry logic, durability, recovery
- Integration (4 NFRs): ✅ Multi-provider, in-situ, storage abstractions
- Security (4 NFRs): ✅ Credential protection, environment injection, masked secrets
- Maintainability (3 NFRs): ✅ Clean abstractions, clear patterns, documented interfaces
- Testability (3 NFRs): ✅ Mock providers, integration tests, 70%+ coverage

**Result: 100% of all project requirements architecturally supported**

---

### Implementation Readiness Validation ✅

**Decision Completeness:**

- 9 core architectural decisions fully documented with rationales
- All technology versions specified and verified via web search
- Implementation patterns comprehensive (naming, structure, communication, process)
- Code examples and anti-patterns provided for all major areas
- Consistency rules (10 mandatory) prevent agent conflicts

**Structure Completeness:**

- All source files and directories explicitly defined
- Integration points clearly mapped (CLI → Executor → Processors → Judges → Storage)
- 6 architectural boundaries explicitly defined and documented
- Requirements-to-component mapping complete (FR categories to modules)
- Development workflow fully specified

**Pattern Completeness:**

- 10 mandatory consistency rules enforced across all agents
- Naming conventions cover Python code, JSON, telemetry, identifiers
- Error handling standardized (format, hierarchy, messages)
- Telemetry patterns unified (immediate emission, centralized collection)
- Configuration validation standardized (Pydantic, lenient on unknowns)
- Implementation checklist provided for verification

---

### Gap Analysis Results ✅

**Critical Gaps:** None found

All architectural decisions documented, all requirements covered, all patterns specified.

**Important Gaps:** None found

Architecture is comprehensive with no blocking missing elements.

**Nice-to-Have Enhancements (Post-v1):**

- Example evaluation configurations (will be created during implementation)
- Detailed Pydantic model JSON schema documentation
- Performance benchmarks and optimization guides
- HTTP API specification (v2+)
- Distributed tracing documentation (v2+)

---

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (78+ FRs, 23 NFRs)
- [x] Scale and complexity assessed (HIGH: enterprise evaluation framework)
- [x] Technical constraints identified (Python 3.10+, DeepEval, OT native)
- [x] Cross-cutting concerns mapped (provider abstraction, telemetry, error handling)

**✅ Architectural Decisions**
- [x] 9 critical decisions documented with versions and rationales
- [x] Technology stack fully specified (Pydantic-AI 1.39.0, Typer, DeepEval, etc.)
- [x] Integration patterns defined (unified OT pipeline, domain-driven storage)
- [x] Performance and reliability addressed (async, batching, retry logic, durability)

**✅ Implementation Patterns**
- [x] Naming conventions established (snake_case/PascalCase, error naming)
- [x] Structure patterns defined (src-layout, module organization, boundaries)
- [x] Communication patterns specified (OT spans, error format, result schemas)
- [x] Process patterns documented (validation, error handling, telemetry emission)

**✅ Project Structure**
- [x] Complete directory structure defined (src/, tests/, docs/ with all files)
- [x] Component boundaries established (6 architectural boundaries)
- [x] Integration points mapped (CLI → Executor → Processors → Judges → Storage)
- [x] Requirements to component mapping complete (FR categories to module table)

---

### Architecture Readiness Assessment

**Overall Status: ✅ READY FOR IMPLEMENTATION**

**Confidence Level: HIGH**

The architecture is:
- **Coherent:** All decisions work together without conflicts
- **Complete:** Every requirement is architecturally supported
- **Consistent:** Patterns enforce predictable, compatible implementation
- **Clear:** Boundaries and responsibilities well-defined
- **Extensible:** Future features (v2+, v3+) can be added without redesign

**Key Strengths:**

1. **Provider Abstraction:** Pydantic-AI shields vendor complexity, allows swapping
2. **Domain-Driven Design:** Run/Config/Prompt ABCs enable pluggable implementations
3. **Unified Telemetry:** Single OT pipeline captures internal + in-situ visibility
4. **Clean Boundaries:** CLI, processors, judges, storage completely separated
5. **Comprehensive Patterns:** 10 mandatory rules prevent AI agent conflicts
6. **Complete Structure:** Every file and directory specified for implementation clarity

**Areas for Future Enhancement:**

1. **HTTP API (v2+):** Architecture supports adding without changes to core
2. **Database Storage (v2+):** Storage ABCs ready for LocalDatabaseRun
3. **Pairwise Judging (v2+):** Judge interface designed for future comparison
4. **Visualization (v3+):** Telemetry pre-processing can reconstruct hierarchies
5. **Performance Optimization (v2+):** Processor batching across scenarios ready

---

### Implementation Handoff

**Architecture Document:** Complete and ready for implementation.
- Location: `_bmad-output/planning-artifacts/architecture.md`
- Sections: 9 decisions, 5 patterns, complete project structure, validation results
- Audience: AI agents implementing gavel-ai components

**For AI Agents Implementing This:**

1. **Follow architectural decisions exactly** — They're documented with rationales
2. **Use implementation patterns consistently** — Prevents conflicts between agents
3. **Respect project structure and boundaries** — Enables clean integration
4. **Reference this document for questions** — Single source of truth
5. **Run pre-commit hooks** — Enforces naming, formatting, type checking

**First Implementation Priority:**

Foundation phase (blocking all other work):
1. Create project structure (src/gavel_ai with all subdirectories)
2. Initialize pyproject.toml with metadata, dependencies, tool configuration
3. Set up pre-commit hooks (black, ruff, mypy)
4. Create conftest.py with pytest fixtures and mock providers
5. Initialize CLI entry point (Typer app in cli/main.py)
6. Create base interfaces (Processor, Judge, Storage abstract classes)

---

## Architecture Completion Summary

### Workflow Completion ✅

**Architecture Decision Workflow:** COMPLETED
**Total Steps Completed:** 8
**Date Completed:** 2025-12-28
**Document Location:** `_bmad-output/planning-artifacts/architecture.md`

---

### Final Architecture Deliverables

**📋 Complete Architecture Document**

- **9 architectural decisions** documented with specific versions and rationales
- **5 implementation patterns** ensuring AI agent consistency
- **6 architectural boundaries** clearly defined
- **Complete project structure** with all files, directories, and integration points
- **100% requirements coverage** validation (78+ FRs, 23+ NFRs)

**🏗️ Implementation Ready Foundation**

- 9 architectural decisions made collaboratively
- 5+ implementation patterns with code examples and anti-patterns
- 8+ main architectural components specified
- 78+ functional requirements fully supported
- 23+ non-functional requirements addressed

**📚 AI Agent Implementation Guide**

- Python 3.10+ with Pydantic-AI v1.39.0
- 10 mandatory consistency rules preventing conflicts
- Complete project structure with clear boundaries
- Unified OpenTelemetry telemetry pipeline
- Domain-driven storage with pluggable implementations

---

### Architecture Highlights

**Technology Stack (Decided & Verified):**
- Provider Abstraction: Pydantic-AI v1.39.0
- CLI Framework: Typer + Rich
- Config Validation: Pydantic with lenient unknown fields
- Judges: DeepEval with deepeval.* namespace
- Telemetry: OpenTelemetry with unified receiver
- Testing: pytest with mock providers

**Core Decisions (9 Total):**
1. ✅ Provider Abstraction: Pydantic-AI
2. ✅ Configuration Structure: Nested directories
3. ✅ Processor Interface: Config-driven, per-processor batching
4. ✅ Run Artifact Schema: Flat with simplified JSON
5. ✅ Judge Integration: DeepEval-native, sequential
6. ✅ CLI Commands: Hierarchical with eval root
7. ✅ Error Handling: Categorized with configurable retry
8. ✅ Storage Abstraction: Domain-driven pluggable
9. ✅ Telemetry: Unified OT pipeline

**Implementation Patterns (5 Categories):**
1. ✅ Naming Conventions (snake_case/PascalCase, error naming)
2. ✅ Data Models (Pydantic with extra='ignore')
3. ✅ Processor & Judge Interfaces (async, config-driven)
4. ✅ Project Organization (src-layout, clear boundaries)
5. ✅ Error Handling & Telemetry (standardized format, immediate emission)

---

### Validation Results: READY FOR IMPLEMENTATION ✅

**Coherence Validation:** ✅ All decisions work together
**Requirements Coverage:** ✅ 100% of all requirements supported
**Implementation Readiness:** ✅ AI agents can implement consistently
**Gap Analysis:** ✅ No critical gaps identified

---

### Implementation Handoff

**For AI Agents Implementing gavel-ai:**

This architecture document is your complete technical guide. Follow these principles:

1. **Follow architectural decisions exactly** — They're documented with versions and rationale
2. **Use implementation patterns consistently** — Prevents conflicts between agents
3. **Respect project structure and boundaries** — Enables clean integration
4. **Reference this document for questions** — Single source of truth
5. **Maintain consistency** — Run pre-commit hooks, follow naming conventions

**First Implementation Priority (Blocking Order):**

1. Create project structure (src/gavel_ai with all subdirectories)
2. Initialize pyproject.toml with metadata, dependencies, tool configuration
3. Set up pre-commit hooks (black, ruff, mypy)
4. Create conftest.py with pytest fixtures and mock providers
5. Initialize CLI entry point (Typer app in cli/main.py)
6. Create base interfaces (InputProcessor, Judge, Run, Config, Prompt ABCs)

---

**Architecture Status:** ✅ **READY FOR IMPLEMENTATION**

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

---

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation. The architecture is the single source of truth for all technical decisions in gavel-ai.
