---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
workflowType: 'epics-and-stories'
lastStep: 4
workflowStatus: 'complete'
completedAt: '2025-12-28'
---

# gavel-ai - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for gavel-ai, decomposing the requirements from the PRD and Architecture into implementable stories organized by user value.

---

## Requirements Inventory

### Functional Requirements (78 FRs across 9 categories)

**FR Category 1 - Setup & Configuration (6 FRs):**
- FR-1.1: CLI scaffolding for new evaluations (`gavel oneshot create --eval <name>`)
- FR-1.2: JSON/YAML configuration persistence (agents.json, eval_config.json, scenarios.json)
- FR-1.3: Provider configurations (agents.json with model definitions and agents)
- FR-1.4: Test scenarios (scenarios.json with structured data or CSV import)
- FR-1.5: Judge customization (DeepEval and custom GEval configuration)
- FR-1.6: Templating and environment variable substitution in configs

**FR Category 2 - Execution & Orchestration (6 FRs):**
- FR-2.1: OneShot local evaluation execution (`gavel oneshot run`)
- FR-2.2: Local LLM provider testing (Claude, GPT, Gemini, Ollama via Pydantic-AI)
- FR-2.3: In-situ deployed system evaluation (HTTP endpoint testing)
- FR-2.4: OpenTelemetry instrumentation (unified pipeline)
- FR-2.5: Selective scenario re-runs (filtering, tagging, resume capability)
- FR-2.6: Reproducible execution flow (deterministic order, traceable execution)

**FR Category 3 - Run Management & Artifacts (7 FRs):**
- FR-3.1: Isolated RunContext creation (timestamped run directories)
- FR-3.2: Complete artifact management (telemetry.jsonl, results.jsonl, manifest.json)
- FR-3.3: Re-judging without re-execution (`gavel oneshot judge --run <run-id>`)
- FR-3.4: Run history tracking (`gavel oneshot list`)
- FR-3.5: Run archival and export (zip/tar.gz with configs and results)
- FR-3.6: Programmatic run inspection API (load run artifacts programmatically)
- FR-3.7: Milestone run marking (`gavel oneshot milestone --run <run-id>`)

**FR Category 4 - Judging & Evaluation (6 FRs):**
- FR-4.1: DeepEval integration (out-of-the-box judges)
- FR-4.2: Declarative GEval configuration (inline or via config file)
- FR-4.3: Pairwise variant comparison scoring (multiple models, multiple prompts)
- FR-4.4: Judge reasoning and scoring (transparent scores with reasoning)
- FR-4.5: Configurable judge execution (retry logic, caching, model selection)
- FR-4.6: Custom judge plugins (extensible interface for custom judges)

**FR Category 5 - Reporting & Result Presentation (6 FRs):**
- FR-5.1: Jinja2 templating system (HTML, Markdown, custom formats)
- FR-5.2: OneShot/SXS report format (summary table, detail cards, judge reasoning)
- FR-5.3: Conversational report format (multi-turn conversation cards)
- FR-5.4: Autotune progression visualization (multi-pass reports with aggregation)
- FR-5.5: Judge reasoning and evidence in reports (expandable sections)
- FR-5.6: Clear winner indication (prominent comparison summary)

**FR Category 6 - Extensibility & Architecture (6 FRs):**
- FR-6.1: Clean abstraction architecture (RunContext, Workflow, Processor, Storage)
- FR-6.2: Workflow extension patterns (Conversational, Autotune documented)
- FR-6.3: Evaluation primitive patterns (Processor, Judge interfaces)
- FR-6.4: Pluggable storage backends (filesystem → future database/S3)
- FR-6.5: Separated presentation tier (CLI now, HTTP API future)
- FR-6.6: Modular dependency management (optional dependencies for advanced features)

**FR Category 7 - CLI Interface & Commands (8 FRs):**
- FR-7.1: Hierarchical command pattern (`gavel [workflow] [action] [options]`)
- FR-7.2: `gavel oneshot create` scaffolding
- FR-7.3: `gavel oneshot run` execution
- FR-7.4: `gavel oneshot judge` re-judging
- FR-7.5: `gavel oneshot report` report generation
- FR-7.6: `gavel oneshot list` run history
- FR-7.7: Structured output formats (JSON for scripting)
- FR-7.8: Help and examples (`gavel --help`, error guidance)

**FR Category 8 - File System & Transparency (7 FRs):**
- FR-8.1: Human-readable artifacts (JSON/JSONL formats)
- FR-8.2: Standard JSON/YAML formats (versionable, diffable)
- FR-8.3: OpenTelemetry format (telemetry.jsonl with standard spans)
- FR-8.4: Results storage format (results.jsonl with scenario/variant/score)
- FR-8.5: Run manifest metadata (timestamp, config hash, counts)
- FR-8.6: Logical directory structure (evaluations/<name>/runs/<timestamp>/)
- FR-8.7: Cleanup and archival (`gavel clean`, manual deletion)

**FR Category 9 - Error Handling & Observability (8 FRs):**
- FR-9.1: Informative error messages (what failed + how to fix)
- FR-9.2: Error categorization (Config, Execution, Validation, System)
- FR-9.3: Debug mode (`--debug` for verbose output)
- FR-9.4: Consistent logging format (standard format in gavel.log)
- FR-9.5: Execution telemetry capture (run_metadata.json with timing stats)
- FR-9.6: Pre-execution validation (schema validation before run)
- FR-9.7: Health checks and diagnostics (`gavel health`, `gavel diagnose`)
- FR-9.8: Accessible telemetry data (in reports and programmatically)

### Non-Functional Requirements (15 NFRs across 7 categories)

**Performance (3 NFRs):**
- NFR-P1: Realistic evaluation execution timelines (2-5s per LLM call)
- NFR-P2: Maximize parallelization and native batching (concurrent scenarios/variants)
- NFR-P3: Efficient resource utilization (<500MB memory, <5% telemetry overhead)

**Reliability (3 NFRs):**
- NFR-R1: Reproducible evaluation execution (deterministic flow, same config = same results)
- NFR-R2: Robust error handling (transient retries with exponential backoff)
- NFR-R3: Data integrity (durable writes, no partial artifacts)

**Integration (3 NFRs):**
- NFR-I1: Multi-provider compatibility (Claude, GPT, Gemini, Ollama via Pydantic-AI)
- NFR-I2: In-situ system integration (HTTP adapters, OpenTelemetry capture)
- NFR-I3: Storage and reporting integration (git-friendly, Jinja2 templates)

**Security (2 NFRs):**
- NFR-S1: Credential protection (masked secrets, env var injection, no plaintext logs)
- NFR-S2: Data confidentiality (local-first, no auto cloud transmission)

**Maintainability (2 NFRs):**
- NFR-M1: Code clarity and extensibility (clean abstractions, interfaces)
- NFR-M2: Documentation for contributors (extension patterns, test helpers)

**Testability (2 NFRs):**
- NFR-T1: Test coverage (70%+ on non-trivial code)
- NFR-T2: Debuggability (debug mode, OT data, clear separation)

### Additional Requirements from Architecture

**Project Setup & Technology Stack:**
- Python 3.10+ (minimum, no strict version barriers on dependencies)
- Pydantic-AI v1.39.0 (provider abstraction)
- Typer CLI framework with Rich
- DeepEval for judges
- OpenTelemetry for telemetry
- Jinja2 for report templating
- pytest for testing

**Starter Template:**
- src-layout project structure
- pyproject.toml as single source of truth
- Pre-commit hooks (black, ruff, mypy)
- Centralized logging configuration

**9 Architectural Decisions (Must Be Implemented):**
1. Pydantic-AI v1.39.0 for provider abstraction
2. Nested directory config structure (config/, data/, prompts/, runs/)
3. Config-driven processor interface with per-processor batching
4. Flat run artifact schema with simplified JSON/JSONL
5. DeepEval-native judges with sequential execution
6. Hierarchical CLI with eval root location and timestamped runs
7. Categorized error handling with exponential backoff retry
8. Domain-driven storage abstraction (Run, Config, Prompt ABCs)
9. Unified OpenTelemetry pipeline with immediate span emission

### FR Coverage Map

| FR Category | Count | Mapped To |
|-------------|-------|-----------|
| Setup & Configuration | 6 FRs | Project Setup Epic |
| Execution & Orchestration | 6 FRs | OneShot Execution Epic |
| Run Management | 7 FRs | Run Management Epic |
| Judging & Evaluation | 6 FRs | Judging & Reporting Epic |
| Reporting | 6 FRs | Judging & Reporting Epic |
| Extensibility | 6 FRs | Architecture Foundation Epic |
| CLI Interface | 8 FRs | CLI & UX Epic |
| File System & Transparency | 7 FRs | Architecture Foundation Epic |
| Error Handling & Observability | 8 FRs | Observability & Quality Epic |

**Total: 78 FRs + 15 NFRs covered across 6 epics**

---

## Epic List

1. **Epic 1: Project Foundation & Setup** - Create project structure, CI/CD, testing infrastructure
2. **Epic 2: CLI & Configuration Management** - CLI framework, scaffolding, config loading
3. **Epic 3: OneShot Execution Pipeline** - Core evaluation execution, processors, provider integration
4. **Epic 4: Judging & Result Evaluation** - Judge integration, DeepEval, result storage
5. **Epic 5: Reporting & Analysis** - Report generation, Jinja2 templates, result presentation
6. **Epic 6: Run Management & Artifact Storage** - RunContext, artifact management, persistence

---

## Epic 1: Project Foundation & Setup

**Epic Goal:** Establish project structure, build infrastructure, testing foundation, and pre-commit standards to enable all subsequent development.

**User Stories:**

### Story 1.1: Initialize Project Structure

As a developer,
I want the project initialized with proper src-layout structure and all required directories,
So that the codebase is organized, scalable, and follows Python best practices.

**Acceptance Criteria:**

- **Given** a fresh git repository
  **When** the project is initialized
  **Then** the directory structure matches the architecture document exactly:
  - src/gavel_ai/ with all submodules (cli, core, processors, judges, storage, reporters, telemetry, log_config)
  - tests/ with unit/, integration/, fixtures/ subdirectories
  - docs/ with quickstart, cli-reference, examples
  - .github/workflows/ with CI/CD pipeline files

- **Given** the project structure is initialized
  **When** inspecting package imports
  **Then** no circular dependencies exist and imports work correctly from src-layout

**Technical Notes:**
- Use src-layout to prevent import masking
- Create __init__.py files with appropriate exports
- Document module organization in architecture document

**Related Requirements:** FR-6.1, FR-6.6, NFR-M1

---

### Story 1.2: Initialize pyproject.toml and Dependencies

As a developer,
I want pyproject.toml configured with correct metadata, dependencies, and tool settings,
So that the project is distributable and all development tools are properly configured.

**Acceptance Criteria:**

- **Given** an empty pyproject.toml
  **When** configured per architecture
  **Then** the following are specified:
  - Project name, version, description
  - Python 3.10+ requirement (no strict version barriers on dependencies)
  - Core dependencies: pydantic-ai>=1.39.0, typer, deepeval, jinja2, pydantic, opentelemetry-api, python-dotenv>=1.0.0
  - Optional development dependencies: pytest, black, ruff, mypy, pre-commit

- **Given** tool configuration in pyproject.toml
  **When** tools are invoked
  **Then** black, ruff, and mypy run with expected configurations

- **Given** the package is built
  **When** installed with `pip install -e .`
  **Then** the gavel command is available and CLI is invokable

**Related Requirements:** NFR-M1, NFR-T1

---

### Story 1.3: Set Up Pre-commit Hooks

As a developer,
I want pre-commit hooks configured to enforce code quality,
So that all committed code follows the project standards.

**Acceptance Criteria:**

- **Given** `.pre-commit-config.yaml` is configured
  **When** `pre-commit install` is run
  **Then** hooks are installed and will run on each commit

- **Given** a code file with formatting/linting/type issues
  **When** the developer attempts to commit
  **Then** pre-commit hooks reject the commit and provide clear guidance

- **Given** code is properly formatted
  **When** pre-commit hooks run
  **Then** the commit proceeds successfully

**Hooks to Configure:**
- black (code formatting)
- ruff (linting)
- mypy (type checking)

**Related Requirements:** NFR-M1

---

### Story 1.4: Set Up pytest Configuration and Basic Test Structure

As a QA engineer,
I want pytest configured with fixtures, mocks, and test structure in place,
So that unit and integration tests can be written immediately.

**Acceptance Criteria:**

- **Given** pytest is configured in pyproject.toml
  **When** tests are run
  **Then** pytest discovers and executes all tests in tests/ directory

- **Given** conftest.py exists
  **When** tests run
  **Then** fixtures (mock providers, sample configs, test data) are available

- **Given** a test file in tests/unit/
  **When** executed with pytest
  **Then** standard logging format is used and test isolation is maintained

- **Given** integration tests in tests/integration/
  **When** executed
  **Then** full workflows can be tested with mock providers (no real API calls)

**Test Structure Setup:**
- tests/conftest.py with pytest configuration
- tests/unit/ directory structure
- tests/integration/ directory structure
- tests/fixtures/ with mock providers and sample data

**Related Requirements:** NFR-T1, NFR-T2

---

### Story 1.5: Create Central Logging Configuration

As a developer,
I want centralized logging setup with standard format,
So that all modules log consistently and observability is clear.

**Acceptance Criteria:**

- **Given** log_config.py exists in src/gavel_ai/
  **When** imported from any module
  **Then** modules receive a configured logger with standard format:
  `"%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"`

- **Given** a module imports and uses the logger
  **When** it writes log messages
  **Then** messages appear in stdout (development) or file (production) with correct format

- **Given** debug mode is enabled
  **When** the application runs
  **Then** DEBUG level logs are included

**Related Requirements:** FR-9.4, FR-9.3

---

### Story 1.6: Initialize OpenTelemetry Setup

As a developer,
I want OpenTelemetry configured and ready for span emission,
So that telemetry instrumentation can be added incrementally.

**Acceptance Criteria:**

- **Given** telemetry.py exists in src/gavel_ai/
  **When** imported
  **Then** `get_tracer()` function is available and returns properly configured tracer

- **Given** a module calls `get_tracer(__name__)`
  **When** it emits spans using the tracer
  **Then** spans are collected by configured OT receiver

- **Given** the application runs
  **When** completed
  **Then** spans have been recorded and are ready for export

- **Given** no OT receiver is configured
  **When** spans are emitted
  **Then** application continues (OT failures don't block execution)

**Implementation Notes:**
- Use OpenTelemetry Python SDK
- Configure simple console exporter for initial testing
- Plan for OTLP exporter in later stories

**Related Requirements:** FR-2.4, Decision 9

---

## Epic 2: CLI & Configuration Management

**Epic Goal:** Build the CLI framework and configuration system that enables users to scaffold, configure, and manage evaluations.

**User Stories:**

### Story 2.1: Build Typer CLI Entry Point and Base Command Structure

As a user,
I want to invoke `gavel [workflow] [action] [options]` from the command line,
So that I can interact with the framework in an intuitive, hierarchical way.

**Acceptance Criteria:**

- **Given** the gavel command is available
  **When** I run `gavel --help`
  **Then** it shows available workflows (oneshot, [conv], [autotune])

- **Given** I run `gavel oneshot --help`
  **When** the command is invoked
  **Then** it shows available actions (create, run, judge, report, list, milestone, health, diagnose)

- **Given** I run `gavel oneshot create --help`
  **When** the command is invoked
  **Then** it shows available options (--eval, --type, etc.) with descriptions

- **Given** I run an invalid command
  **When** the command fails
  **Then** a helpful error message appears with usage guidance

**Related Requirements:** FR-7.1, FR-7.2, FR-7.8

---

### Story 2.2: Implement `gavel oneshot create` Scaffolding

As a user,
I want to scaffold a new evaluation with `gavel oneshot create --eval <name>`,
So that I can get started quickly with a pre-configured evaluation structure.

**Acceptance Criteria:**

- **Given** I run `gavel oneshot create --eval my_eval`
  **When** the command completes
  **Then** the following structure is created:
  ```
  <eval-root>/my_eval/
  ├── config/
  │   ├── agents.json        # With sample model definitions
  │   ├── eval_config.json   # With evaluation setup
  │   ├── async_config.json  # With async/concurrency settings
  │   └── judges/            # Empty, for judge configs
  ├── data/
  │   ├── scenarios.json     # Sample scenarios
  │   └── scenarios.csv      # Alternative CSV format
  ├── prompts/
  │   └── default.toml       # Sample prompt template
  └── runs/                  # Empty, for run outputs
  ```

- **Given** the scaffolded evaluation exists
  **When** I inspect the config files
  **Then** they contain sensible defaults that can be modified

- **Given** I modify the scaffolded config
  **When** I run the evaluation
  **Then** my customizations are respected

**Default Configurations:**
- agents.json: Sample Claude and GPT definitions
- eval_config.json: Basic OneShot setup
- scenarios.json: Sample scenarios with placeholders
- prompts: Default prompt template

**Related Requirements:** FR-1.1, FR-1.2, FR-7.2

---

### Story 2.3: Implement Config Loading and Validation

As a developer,
I want configuration files to be loaded and validated at startup,
So that configuration errors are caught early with clear messages.

**Acceptance Criteria:**

- **Given** a valid config file exists
  **When** it is loaded
  **Then** it is parsed and validated using Pydantic with `extra='ignore'`

- **Given** a config file is missing required fields
  **When** it is loaded
  **Then** a ConfigError is raised with a clear message explaining what's missing

- **Given** a config file contains unknown fields
  **When** it is loaded
  **Then** those fields are silently ignored (forward compatible)

- **Given** a config file has type mismatches
  **When** it is loaded
  **Then** a ValidationError is raised with guidance on fixing the issue

- **Given** environment variables are referenced (e.g., {{ANTHROPIC_API_KEY}})
  **When** the config is loaded
  **Then** environment variables are substituted using the `{{VAR_NAME}}` pattern

- **Given** a `.env` file exists in the project root
  **When** the CLI starts
  **Then** environment variables are automatically loaded via `python-dotenv`

- **Given** an environment variable is missing
  **When** referenced in a config file
  **Then** a ConfigError is raised with helpful message: "Environment variable 'VAR_NAME' not set - Set VAR_NAME environment variable or provide value directly"

**Configuration Files to Support:**
- agents.json (Pydantic model definition)
- eval_config.json (Evaluation configuration)
- async_config.json (Async/concurrency settings)
- Judge config files in config/judges/
- Scenarios in data/ (JSON or CSV)
- Prompts in prompts/ (TOML format)

**Related Requirements:** FR-1.2, FR-1.3, FR-1.4, FR-1.6, FR-9.6

**Implementation Note (2026-01-01):**
- Added `python-dotenv>=1.0.0` to `pyproject.toml` dependencies
- CLI (`src/gavel_ai/cli/main.py`) now calls `load_dotenv(verbose=False, override=False)` in main callback
- Created `.env.example` template with example API key placeholders
- Updated test evaluation (`test_os/config/agents.json`) to use `{{ANTHROPIC_API_KEY}}` syntax
- Added 4 unit tests in `tests/unit/test_dotenv_loading.py` verifying:
  - load_dotenv called on CLI startup
  - Environment variable substitution works correctly
  - Missing variables raise helpful ConfigError
  - Correct parameters (verbose=False, override=False)
- Created `SETUP.md` with complete .env configuration guide
- Updated README.md and docs/quickstart/getting-started.md with .env setup instructions

---

### Story 2.4: Implement Agents Configuration Schema

As a user,
I want to define agents (provider + model + prompt combinations) in agents.json,
So that I can test multiple models with different prompts in a single evaluation.

**Acceptance Criteria:**

- **Given** agents.json with _models and agents sections
  **When** the config is loaded
  **Then** model definitions (_models) are parsed with provider, version, parameters

- **Given** agents reference model_id and prompt_ref
  **When** the config is loaded
  **Then** agents are correctly linked to shared models

- **Given** an agent configuration
  **When** used in evaluation
  **Then** the correct provider (Pydantic-AI) is invoked with correct parameters

**agents.json Schema:**
```json
{
  "_models": {
    "claude": {
      "provider": "anthropic",
      "model_version": "claude-3-5-sonnet-20241022",
      "parameters": {"temperature": 0.7, "max_tokens": 4096}
    }
  },
  "agents": [
    {
      "id": "agent-1",
      "model_id": "claude",
      "prompt_ref": "prompt-name:v1",
      "parameters": {}
    }
  ]
}
```

**Related Requirements:** FR-1.3, Decision 1

---

### Story 2.5: Implement Scenarios Configuration

As a user,
I want to define test scenarios in scenarios.json or scenarios.csv,
So that I can easily manage test cases and bulk import data.

**Acceptance Criteria:**

- **Given** scenarios.json with array of scenarios
  **When** the config is loaded
  **Then** each scenario has: id, input (dict or key/value), expected_behavior (optional)

- **Given** scenarios.csv with columns
  **When** the config is loaded
  **Then** columns are mapped to scenario input fields

- **Given** a scenario defines input with placeholders (e.g., {{user_input}})
  **When** the evaluation runs
  **Then** placeholders are substituted from scenario data

- **Given** 100+ scenarios
  **When** they are loaded
  **Then** performance is acceptable (<1s load time)

**Scenarios Format:**
```json
{
  "scenarios": [
    {
      "id": "scenario-1",
      "input": {
        "user_input": "What is the capital of France?",
        "context": "General knowledge"
      },
      "expected_behavior": "Accurate answer"
    }
  ]
}
```

**Related Requirements:** FR-1.4

---

### Story 2.6: Implement Judge Configuration Schema

As a user,
I want to configure DeepEval judges (built-in and custom GEval) in eval_config.json,
So that I can define evaluation criteria without modifying code.

**Acceptance Criteria:**

- **Given** eval_config.json includes judges array
  **When** the config is loaded
  **Then** judges are parsed with deepeval name, threshold, custom criteria

- **Given** a judge references a file in config/judges/
  **When** the config is loaded
  **Then** the file is loaded and merged with the judge config

- **Given** a judge definition is invalid
  **When** the config is loaded
  **Then** a JudgeError is raised with guidance

**Judges Configuration:**
```json
{
  "judges": [
    {
      "id": "similarity",
      "deepeval_name": "deepeval.similarity",
      "config": {"threshold": 0.8}
    },
    {
      "id": "custom",
      "deepeval_name": "deepeval.geval",
      "config_ref": "judges/custom.json"
    }
  ]
}
```

**Related Requirements:** FR-1.5, FR-4.1, FR-4.2, Decision 5

---

## Epic 3: OneShot Execution Pipeline

**Epic Goal:** Build the core execution engine that runs scenarios against agents, collects outputs, and coordinates telemetry.

**User Stories:**

### Story 3.1: Create Processor Base Classes and Interface

As a developer,
I want clean, well-defined processor interfaces,
So that different processor types can be implemented consistently.

**Acceptance Criteria:**

- **Given** InputProcessor ABC is defined
  **When** examined
  **Then** it has:
  - `__init__(config: ProcessorConfig)` constructor
  - `async process(inputs: List[Input]) -> ProcessorResult` method
  - Tracer setup via `get_tracer(__name__)`

- **Given** a concrete processor implements InputProcessor
  **When** the interface contract is checked
  **Then** the implementation provides all required methods with correct signatures

- **Given** ProcessorConfig Pydantic model is defined
  **When** validated
  **Then** it uses `extra='ignore'` for forward compatibility

**Related Requirements:** FR-6.1, FR-6.3, Decision 3

---

### Story 3.2: Implement PromptInputProcessor

As a user,
I want to evaluate prompts against scenarios locally,
So that I can test prompts and model behavior before deployment.

**Acceptance Criteria:**

- **Given** PromptInputProcessor is initialized with a prompt and agent
  **When** process() is called with a scenario
  **Then** the prompt is rendered with scenario inputs and sent to the agent

- **Given** an agent is configured (provider, model, temperature, etc.)
  **When** the processor executes
  **Then** the correct provider (Pydantic-AI) is invoked with correct parameters

- **Given** the LLM call completes
  **When** the processor returns
  **Then** ProcessorResult contains: output (string), metadata (tokens, latency), optional error

- **Given** telemetry is enabled
  **When** the processor runs
  **Then** an OT span "processor.execute" is emitted with:
  - processor.type = "prompt_input"
  - scenario.id, variant.id, subject.id attributes
  - Timing information

**Related Requirements:** FR-2.1, FR-2.2, FR-2.4, Decision 1, Decision 3

---

### Story 3.3: Implement ClosedBoxInputProcessor

As a user,
I want to evaluate deployed in-situ systems (HTTP endpoints),
So that I can test production models and endpoints.

**Acceptance Criteria:**

- **Given** ClosedBoxInputProcessor is configured with an endpoint URL
  **When** process() is called with a scenario
  **Then** an HTTP request is made to the endpoint with scenario data

- **Given** the endpoint responds
  **When** the processor completes
  **Then** ProcessorResult contains: output (response), metadata (status, latency), optional error

- **Given** the endpoint is unavailable
  **When** the processor is invoked
  **Then** a ProcessorError is raised with recovery guidance

- **Given** telemetry is enabled
  **When** the processor runs
  **Then** an OT span is emitted with in-situ endpoint details

**Related Requirements:** FR-2.3, FR-2.4, Decision 3

---

### Story 3.4: Implement ScenarioProcessor (for Conversational Workflows)

As a developer,
I want to handle multi-turn conversations,
So that conversational evaluation workflows can be supported (v2+).

**Acceptance Criteria:**

- **Given** ScenarioProcessor wraps an InputProcessor
  **When** a multi-turn scenario is executed
  **Then** the InputProcessor is called once per turn with context from prior turns

- **Given** context accumulates across turns
  **When** the processor executes turn N
  **Then** previous turn outputs are available in the context

- **Given** the scenario completes
  **When** the processor returns
  **Then** the full conversation is captured in the result

**Note:** This story is included in the epic structure but may be deferred to v2 depending on MVP scope.

**Related Requirements:** FR-6.2

---

### Story 3.5: Implement Executor (Orchestration & Concurrency)

As a developer,
I want an executor that orchestrates processor execution,
So that multiple scenarios and variants can be processed efficiently.

**Acceptance Criteria:**

- **Given** an Executor is configured with processor and scenarios
  **When** execute() is called
  **Then** scenarios are processed concurrently based on configured parallelism level

- **Given** error_handling is set to "collect_all"
  **When** a scenario fails
  **Then** execution continues, and the error is reported in results

- **Given** error_handling is set to "fail_fast"
  **When** a scenario fails
  **Then** execution stops immediately and the error is raised

- **Given** telemetry is enabled
  **When** execution completes
  **Then** parent span "executor.run" wraps all processor spans

- **Given** concurrency is configured
  **When** execution runs
  **Then** parallelism respects the configured level (e.g., 4 concurrent tasks)

**Related Requirements:** FR-2.1, FR-2.5, Decision 3

---

### Story 3.6: Implement Provider Abstraction with Pydantic-AI Integration

As a developer,
I want provider calls abstracted via Pydantic-AI,
So that new providers can be added without changing processor code.

**Acceptance Criteria:**

- **Given** Pydantic-AI v1.39.0 is integrated
  **When** a processor invokes an agent
  **Then** it uses Pydantic-AI's provider abstraction layer

- **Given** a model is configured with anthropic provider
  **When** invoked
  **Then** Claude is called with correct parameters

- **Given** a model is configured with openai provider
  **When** invoked
  **Then** GPT is called with correct parameters

- **Given** a request fails (timeout, rate limit, auth)
  **When** the error is caught
  **Then** it's wrapped in ProcessorError with recovery guidance

- **Given** telemetry is enabled
  **When** an LLM call is made
  **Then** an OT span "llm.call" is emitted with: provider, model, tokens, latency

- **Given** an agent is created with `output_type=str` (default)
  **When** the agent is invoked
  **Then** the response.output is a string with raw text

- **Given** an agent is created with `output_type=PydanticModel`
  **When** the agent is invoked
  **Then** the response.output is a validated Pydantic model instance (type-safe)

**Enhancement Notes (2026-01-01):**

The `ProviderFactory.create_agent()` method now supports configurable output types via the `output_type` parameter:

- **Default behavior**: `output_type=str` returns raw text responses (maintains backward compatibility)
- **Structured outputs**: `output_type=PydanticModel` enables type-safe, validated responses for specialized components
- **Use cases**:
  - Processors: Use default `str` for flexible text processing
  - Judges: Use structured models like `JudgeVerdict(winner, confidence, reasoning)` for type safety
  - Reporters: Use structured models for formatted outputs

**Example:**
```python
# Default: raw text
agent = factory.create_agent(model_def)
result = await agent.run(prompt)
text: str = result.output

# Structured: type-safe verdict
class JudgeVerdict(BaseModel):
    winner: Literal["subject", "baseline", "tie"]
    confidence: float
    reasoning: str

agent = factory.create_agent(model_def, output_type=JudgeVerdict)
result = await agent.run(prompt)
verdict: JudgeVerdict = result.output  # Validated!
```

**Related Requirements:** FR-2.2, Decision 1, FR-2.4

---

### Story 3.7: Implement Timeout and Retry Logic

As a user,
I want automatic retry of transient failures,
So that temporary API issues don't fail the evaluation.

**Acceptance Criteria:**

- **Given** an LLM call times out
  **When** retry is configured
  **Then** the call is retried up to max_retries times with exponential backoff

- **Given** a rate limit error occurs
  **When** retry is configured
  **Then** it's classified as transient and retried

- **Given** an auth failure occurs
  **When** retry is configured
  **Then** it's classified as non-transient and fails immediately (no retry)

- **Given** max_retries is exceeded
  **When** the evaluation continues
  **Then** the error is reported in results or collection stops based on error_handling

**Retry Configuration:**
- initial_retry_delay: 1 second
- max_retry_delay: 30 seconds
- backoff_factor: 2 (exponential with jitter)
- max_retries: 3 (configurable per eval)

**Related Requirements:** FR-2.1, NFR-R2, Decision 7

---

### Story 3.8: Wire CLI `gavel oneshot run` to Execution Pipeline

As a user,
I want `gavel oneshot run --eval <name>` to execute my evaluation end-to-end,
So that I can run scenarios, judge results, and generate reports with a single command.

**Acceptance Criteria:**

- **Given** I run `gavel oneshot run --eval test_os`
  **When** the command completes successfully
  **Then**:
  - RunContext is created with timestamped run directory
  - Config files are loaded and validated
  - Processor executes all scenarios
  - Judges evaluate all results
  - Results are stored in results.jsonl
  - Telemetry is captured in telemetry.jsonl
  - Report is generated (report.html)
  - Run manifest is saved (manifest.json)

- **Given** valid config files exist in `.gavel/evaluations/<eval>/config/`
  **When** `gavel oneshot run` executes
  **Then**:
  - agents.json is loaded and validated
  - eval_config.json is loaded and validated
  - async_config.json is loaded and validated
  - scenarios.json is loaded and validated
  - All Pydantic validation errors produce helpful messages

- **Given** the evaluation directory doesn't exist
  **When** `gavel oneshot run --eval missing_eval` is executed
  **Then** ConfigError is raised: "Evaluation 'missing_eval' not found - Run 'gavel oneshot create' first"

- **Given** `--scenarios 1-5` option is provided
  **When** execution runs
  **Then** only scenarios 1-5 are executed

- **Given** I run the same evaluation twice
  **When** both runs complete
  **Then** separate run directories exist with unique timestamps

**Technical Notes:**
- Orchestrates all components: ConfigLoader → RunContext → Processor → Executor → Judges → Storage → Report
- Replaces stub implementation in `src/gavel_ai/cli/workflows/oneshot.py:run()`
- Creates ConfigLoader class for config file orchestration
- Wires all backend infrastructure built in Epics 2-6

**Related Requirements:** FR-2.1, FR-7.3, FR-3.1, FR-3.2, FR-9.1

---

### Story 3.9: Refactor OneShot Run Method for Maintainability

As a developer,
I want the oneshot `run()` method refactored from a 400-line monolithic function into isolated, testable steps,
So that the codebase is easier to maintain, extend, and test.

**Acceptance Criteria:**

- **Given** EvalContext class exists
  **When** examined
  **Then**:
  - It loads eval_config, agents_config, scenarios on demand (lazy-loading)
  - It caches prompt templates
  - It is immutable (no setters, read-only properties)

- **Given** RunContext class exists
  **When** examined
  **Then**:
  - It wraps LocalFilesystemRun for artifact persistence
  - It holds validation_result, processor_results, evaluation_results, report_content, run_metadata
  - It provides type-safe property getters/setters for step outputs

- **Given** Step abstract base class exists
  **When** examined
  **Then**:
  - It has abstract `execute(context: RunContext)` method
  - It has `_safe_execute(context: RunContext)` wrapper with error handling
  - It has `phase: StepPhase` property identifying the step

- **Given** four concrete Step implementations exist (Validator, ScenarioProcessor, JudgeRunner, ReportRunner)
  **When** examined
  **Then**:
  - ValidatorStep validates eval_config, agents_config, scenarios
  - ScenarioProcessorStep executes scenarios through processor
  - JudgeRunnerStep executes judges on results
  - ReportRunnerStep exports results and generates reports

- **Given** the refactored run() method is invoked
  **When** it executes
  **Then**:
  - It creates EvalContext and RunContext
  - It iterates through steps in order (validator → processor → judge → reporter)
  - It calls step._safe_execute() for each step
  - It exits on first failure (fail-fast)

- **Given** all existing tests are run
  **When** they execute
  **Then**:
  - All 387+ existing tests pass
  - No regressions in functionality

- **Given** unit tests are written for the refactored code
  **When** executed
  **Then**:
  - Each Step is tested in isolation with mock contexts
  - EvalContext lazy-loading is tested
  - RunContext state management is tested
  - Step error handling is tested

**Technical Notes:**
- Resolves complexity violation (current run() is C901=11, max=10)
- Enables future workflow variants (Conversational, Autotune) via Step inheritance
- Provides type-safe step output contracts via properties
- Extracted logic maps to current run() line ranges:
  - ValidatorStep: lines 126-143
  - ScenarioProcessorStep: lines 173-244
  - JudgeRunnerStep: lines 247-318
  - ReportRunnerStep: lines 320-444

**Related Requirements:** FR-6.1, NFR-M1, NFR-T1, NFR-M2

**Tech Spec:** `_bmad-output/planning-artifacts/tech-specs/3-9-refactor-oneshot-run-method.md`

---

## Epic 4: Judging & Result Evaluation

**Epic Goal:** Build the judging system that evaluates outputs from processors and produces scored results.

**User Stories:**

### Story 4.1: Create Judge Base Class and Interface

As a developer,
I want a clean judge interface,
So that different judge implementations can be plugged in consistently.

**Acceptance Criteria:**

- **Given** Judge ABC is defined
  **When** examined
  **Then** it has:
  - `__init__(config: JudgeConfig)` constructor
  - `async evaluate(scenario: Scenario, subject_output: str) -> JudgeResult` method
  - Tracer setup

- **Given** JudgeResult Pydantic model is defined
  **When** examined
  **Then** it has: score (int, 1-10), reasoning (optional str), evidence (optional str)

**Related Requirements:** FR-6.1, FR-6.3, Decision 5

---

### Story 4.2: Integrate DeepEval Judges

As a user,
I want to use DeepEval judges out-of-the-box,
So that I have immediate access to proven evaluation logic.

**Acceptance Criteria:**

- **Given** DeepEval is installed
  **When** a judge is configured with deepeval.similarity
  **Then** the DeepEval similarity judge is instantiated

- **Given** a judge is configured with deepeval.faithfulness
  **When** evaluate() is called
  **Then** the DeepEval faithfulness logic is executed

- **Given** a DeepEval judge completes
  **When** it returns
  **Then** the result is wrapped in JudgeResult with score (1-10) and reasoning

- **Given** a DeepEval judge fails
  **When** the error occurs
  **Then** it's wrapped in JudgeError with recovery guidance

**Supported DeepEval Judges:**
- deepeval.similarity
- deepeval.faithfulness
- deepeval.hallucination
- deepeval.answer_relevancy
- [Others as available in DeepEval]

**Related Requirements:** FR-4.1, Decision 5

---

### Story 4.3: Implement Custom GEval Judge Support

As a user,
I want to define custom evaluation criteria using GEval,
So that I can evaluate domain-specific aspects not covered by built-in judges.

**Acceptance Criteria:**

- **Given** a judge is configured with deepeval.geval
  **When** the judge config includes criteria and evaluation steps
  **Then** GEval is instantiated with that configuration

- **Given** GEval is executed
  **When** it completes
  **Then** it produces a score (1-10) and reasoning

- **Given** GEval configuration is complex/lengthy
  **When** it's stored in config/judges/custom.json
  **Then** the judge config references it and merges correctly

**GEval Configuration:**
```json
{
  "criteria": "Technical accuracy and clarity",
  "evaluation_steps": [
    "Check factual accuracy",
    "Evaluate explanation clarity"
  ],
  "model": "claude-3-5-sonnet"
}
```

**Related Requirements:** FR-4.2, Decision 5

---

### Story 4.4: Implement Judge Registry and Factory

As a developer,
I want judges to be discovered and instantiated via a registry,
So that judges can be added/removed without modifying core code.

**Acceptance Criteria:**

- **Given** JudgeRegistry exists
  **When** judges are registered
  **Then** they can be instantiated by name

- **Given** a judge name is referenced in config
  **When** JudgeRegistry.create(judge_name, config) is called
  **Then** the correct judge implementation is instantiated

- **Given** a judge name is not found
  **When** instantiation is attempted
  **Then** a clear error message indicates available judges

**Related Requirements:** FR-4.5, FR-4.6

---

### Story 4.5: Implement Sequential Judge Execution

As a developer,
I want judges to execute sequentially,
So that results are evaluated consistently without race conditions (parallel support planned for v2+).

**Acceptance Criteria:**

- **Given** multiple judges are configured
  **When** execution runs
  **Then** Judge A evaluates all outputs, then Judge B evaluates all outputs, etc.

- **Given** judge A completes
  **When** judge B starts
  **Then** both judges' results are preserved in the result object

- **Given** judge A fails
  **When** error handling is configured
  **Then** either execution stops or the error is recorded based on error_handling

**Related Requirements:** Decision 5

---

### Story 4.6: Implement Result Storage (Two-File Design)

As a developer,
I want processor outputs stored immutably and judge evaluations stored mutably,
So that results can be re-judged without re-executing processors and results are reproducible.

**Updated Design (2026-01-01):**

The results storage now uses a **two-file design** for clean separation of concerns:
- **results_raw.jsonl** — Immutable processor execution record
- **results_judged.jsonl** — Mutable judgment layer (regenerable when judges change)

**Acceptance Criteria:**

**results_raw.jsonl (Immutable):**
- **Given** a processor produces an output
  **When** execution completes
  **Then** a single JSON line is written to results_raw.jsonl with:
  - scenario_id
  - variant_id (model/agent)
  - processor_type ("prompt_input", "closedbox_input", etc.)
  - processor_output (complete LLM response)
  - timing_ms (end-to-end latency)
  - tokens_prompt (input tokens)
  - tokens_completion (output tokens)
  - error (null if success, error message if failed)
  - timestamp (ISO 8601)

- **Given** 1000 scenarios are processed
  **When** results_raw.jsonl is examined
  **Then** each result is on its own line (JSONL format) with no judges array

- **Given** results_raw.jsonl exists
  **When** it's inspected
  **Then** it contains only processor execution data (no judge scores)

**results_judged.jsonl (Mutable):**
- **Given** all processors complete and judges execute
  **When** evaluation completes
  **Then** results_judged.jsonl is written with one line per (scenario × variant × processor) combo containing:
  - All fields from results_raw.jsonl
  - judges array: multiple judge results per entry
    - judge_id, judge_name, judge_score (1-10), judge_reasoning, judge_evidence

- **Given** results_judged.jsonl is examined
  **When** judges are checked
  **Then** multiple judges per entry are supported (judges array)

- **Given** an evaluation has no judges configured
  **When** results_judged.jsonl is written
  **Then** the judges array is empty []

**Immutability Contract:**
- Once results_raw.jsonl is written, it never changes (source of truth for execution)
- results_judged.jsonl can be regenerated from results_raw.jsonl without re-running processors
- Supports FR-3.3: Re-judge existing runs without re-execution

**Related Requirements:** FR-3.2, FR-8.4, Decision 4, FR-3.3

---

### Story 4.7: Export results_raw.jsonl from Processor Outputs

As a developer,
I want processor outputs automatically exported to results_raw.jsonl,
So that execution records are immutable and available for re-judging.

**Acceptance Criteria:**

- **Given** processors complete execution
  **When** results are saved
  **Then** results_raw.jsonl is created with one JSONL entry per (scenario × variant × processor) combo

- **Given** processor output data exists
  **When** exported to results_raw.jsonl
  **Then** each entry contains:
  - scenario_id (from input)
  - variant_id (from model/agent)
  - processor_type (from processor config)
  - processor_output (complete LLM response string)
  - timing_ms (latency from ProcessorResult)
  - tokens_prompt (input tokens from ProcessorResult)
  - tokens_completion (output tokens from ProcessorResult)
  - error (null if success, error message if failed)
  - timestamp (ISO 8601 format)

- **Given** 1000 processor results are exported
  **When** results_raw.jsonl is examined
  **Then** it has 1000 lines (JSONL format, one entry per line)

- **Given** results_raw.jsonl is written
  **When** the file is created
  **Then** it's writable to disk atomically (no partial writes)

**Implementation Notes:**
- Export happens in `oneshot.py:run()` after executor completes (step 7)
- File written to: `run_dir / "results_raw.jsonl"`
- Uses jsonlines library for JSONL writing
- Timestamp uses datetime.now(timezone.utc).isoformat()

**Related Requirements:** FR-3.2, FR-8.4, Decision 4

---

### Story 4.8: Export results_judged.jsonl with Judge Evaluations

As a developer,
I want judge evaluations automatically exported to results_judged.jsonl,
So that complete evaluation results are available for reporting and analysis.

**Acceptance Criteria:**

- **Given** processors complete AND judges evaluate all results
  **When** results are saved
  **Then** results_judged.jsonl is created with one JSONL entry per (scenario × variant × processor) combo

- **Given** judge evaluation data exists
  **When** exported to results_judged.jsonl
  **Then** each entry contains:
  - All fields from results_raw.jsonl (scenario_id, processor_output, timing_ms, etc.)
  - judges array with multiple judge results (even if empty):
    - judge_id (unique judge identifier)
    - judge_name (e.g., "deepeval.similarity")
    - judge_score (integer 1-10)
    - judge_reasoning (human-readable explanation)
    - judge_evidence (supporting details)

- **Given** no judges are configured
  **When** results_judged.jsonl is exported
  **Then** the judges array is empty [] for each entry

- **Given** multiple judges are configured
  **When** results_judged.jsonl is exported
  **Then** each entry has N judge objects (one per judge)

- **Given** results_judged.jsonl is written
  **When** the file is created
  **Then** it can be re-created from results_raw.jsonl without re-running processors

**Implementation Notes:**
- Export happens in `oneshot.py:run()` after judge_executor completes (step 8)
- File written to: `run_dir / "results_judged.jsonl"`
- Can be regenerated by running judges again on results_raw.jsonl data
- Supports FR-3.3 (re-judge workflow)

**Related Requirements:** FR-3.2, FR-8.4, Decision 4, FR-3.3

---

### Story 4.9: Implement Re-judging Capability

As a user,
I want to re-judge existing results without re-running evaluations,
So that I can iterate on judge definitions without expensive API calls.

**Acceptance Criteria:**

- **Given** a completed run with results_raw.jsonl
  **When** `gavel oneshot judge --run <run-id>` is invoked
  **Then** results_raw.jsonl is loaded and judges are re-applied to create new results_judged.jsonl

- **Given** new judges are added to eval config
  **When** re-judging runs
  **Then** new judge results are computed and written to results_judged.jsonl

- **Given** judge definitions change
  **When** re-judging runs
  **Then** results_judged.jsonl is completely regenerated with all judges (old and new)

- **Given** re-judging completes
  **When** examined
  **Then** execution is fast (<1s for typical eval) since no LLM calls are made (judges only evaluate stored outputs)

- **Given** re-judging finishes
  **When** report is regenerated
  **Then** report.html is updated with new judge scores

**Implementation Notes:**
- Load results_raw.jsonl from existing run
- Apply judges from current eval config
- Write new results_judged.jsonl (overwrites previous version)
- results_raw.jsonl remains unchanged
- No LLM processor calls needed

**Related Requirements:** FR-3.3, FR-3.2

---

## Epic 5: Reporting & Analysis

**Epic Goal:** Generate human-readable reports that help users understand evaluation results and make decisions.

**User Stories:**

### Story 5.1: Implement Reporter Base Class and Interface

As a developer,
I want a clean reporter interface,
So that different report formats can be implemented consistently.

**Acceptance Criteria:**

- **Given** Reporter ABC is defined
  **When** examined
  **Then** it has:
  - `async generate(run: Run, template: str) -> str` method
  - Support for multiple output formats

**Related Requirements:** FR-6.1

---

### Story 5.2: Implement Jinja2-Based Report Generation

As a developer,
I want report templates to be Jinja2-based,
So that users can customize report format and layout.

**Acceptance Criteria:**

- **Given** a Jinja2 template exists
  **When** report generation runs
  **Then** the template is rendered with context variables

- **Given** template variables like {{title}}, {{overview}}, {{summary}}, {{results}}, {{telemetry}}
  **When** the template references them
  **Then** they're substituted with actual data

- **Given** a custom template is provided
  **When** report is generated
  **Then** the custom template is used instead of default

**Template Variables Available:**
- title: Evaluation name
- overview: Eval details (local vs in-situ, variants)
- summary: Table of aggregate scores per variant
- results: Detailed results per scenario
- telemetry: Timing, token counts, metrics
- metadata: Run timestamp, config hash, counts

**Related Requirements:** FR-5.1

---

### Story 5.3: Implement OneShot Report Format

As a user,
I want OneShot reports to show which variant is better and why,
So that I can make confident decisions about model/prompt choices.

**Acceptance Criteria:**

- **Given** a completed OneShot evaluation
  **When** report is generated
  **Then** the report includes:
  - Title: Evaluation name and date
  - Overview: Variants tested, judge definitions
  - Summary: One table showing each variant's scores and total
  - Detail: One section per scenario with:
    - Scenario input (expandable)
    - Variant outputs table with judge scores
    - Judge reasoning (expandable)
  - Winner indication: Prominent display of best variant

- **Given** the report is opened in a browser
  **When** viewed
  **Then** it's readable, formatted clearly, and expandable sections work

- **Given** the report is converted to Markdown
  **When** examined
  **Then** it's readable and includes all information

**Report Output:**
- Default: HTML (report.html in run directory)
- Alternative: Markdown (report.md)

**Related Requirements:** FR-5.2, FR-5.5, FR-5.6

---

### Story 5.4: Implement Conversational Report Format

As a user,
I want conversational evaluations to show full conversations with judge evaluations,
So that I can understand how models behave in multi-turn contexts (v2+).

**Acceptance Criteria:**

- **Given** a completed conversational evaluation
  **When** report is generated
  **Then** the report includes:
  - Full conversation history per scenario
  - Judge evaluations of each turn or final conversation
  - Variant comparison

**Note:** This story may be deferred to v2 depending on MVP scope.

**Related Requirements:** FR-5.3

---

### Story 5.5: Implement Autotune Progression Report

As a user,
I want autotune reports to show prompt evolution and improvement,
So that I can see how optimization progresses (v3+).

**Acceptance Criteria:**

- **Given** a completed autotune run with multiple passes
  **When** report is generated
  **Then** individual reports for each pass are generated
  - report-pass-1.html, report-pass-2.html, etc.
  - report-aggregate.html showing progression

- **Given** the aggregate report is viewed
  **When** examined
  **Then** it shows judge scores over passes, enabling trend analysis

**Note:** This story is deferred to v3.

**Related Requirements:** FR-5.4

---

## Epic 6: Run Management & Artifact Storage

**Epic Goal:** Store evaluation runs with complete artifacts, enable run history tracking, archival, and programmatic access.

**User Stories:**

### Story 6.1: Create Run and Config Abstract Base Classes

As a developer,
I want pluggable storage abstractions,
So that storage can be changed (filesystem → database → S3) without modifying business logic.

**Acceptance Criteria:**

- **Given** Run ABC is defined
  **When** examined
  **Then** it has:
  - `save()` method to persist artifacts
  - `load(run_id)` static method to retrieve
  - `artifacts` property with Dict[str, ArtifactRef]

- **Given** Config ABC is defined
  **When** examined
  **Then** it provides interface for loading/saving configs

- **Given** Prompt ABC is defined
  **When** examined
  **Then** it provides interface for loading/saving prompts

**Related Requirements:** FR-6.1, FR-6.4, Decision 8

---

### Story 6.2: Implement LocalFilesystemRun Storage

As a developer,
I want runs stored on the filesystem,
So that v1 evaluations are simple, versionable, and human-readable.

**Acceptance Criteria:**

- **Given** an evaluation completes
  **When** run is saved
  **Then** the run directory is created at: `.gavel/evaluations/<eval-name>/runs/run-<YYYYMMDD-HHMMSS>/`

- **Given** the run directory exists
  **When** artifacts are saved
  **Then** they're stored in the correct locations:
  - manifest.json
  - config/ (copy of all eval configs)
  - telemetry.jsonl
  - results_raw.jsonl (immutable processor outputs)
  - results_judged.jsonl (judge evaluations)
  - run_metadata.json
  - gavel.log
  - report.html

- **Given** a run is completed
  **When** it's examined on disk
  **Then** all files are readable, inspectable, and versionable (git-friendly)

**Related Requirements:** FR-3.1, FR-3.2, FR-8.6, Decision 8

---

### Story 6.2.1: Populate config/ Directory with Evaluation Configs

As a developer,
I want evaluation configs copied to the run directory,
So that runs are self-contained, reproducible, and auditable.

**Acceptance Criteria:**

- **Given** an evaluation runs
  **When** the run directory is created
  **Then** the following configs are copied to `run_dir/config/`:
  - agents.json
  - eval_config.json
  - async_config.json
  - scenarios.json (or scenarios.csv)
  - All judge configs from config/judges/

- **Given** a run has completed
  **When** I inspect `run_dir/config/`
  **Then** the configs are readable and match the original eval configs

- **Given** the original eval config changes
  **When** an old run is examined
  **Then** the original config is still available in `run_dir/config/`

- **Given** 100+ config files exist
  **When** run directory is created
  **Then** all configs are copied efficiently (no performance issues)

**Implementation Notes:**
- Copy happens during `LocalFilesystemRun.save()` or in `oneshot.py:run()` before execution starts
- Source: `.gavel/evaluations/<eval>/config/`
- Destination: `run_dir/config/`
- Use shutil.copytree or similar for directory copying
- Handle empty judge configs directory gracefully

**Related Requirements:** FR-3.1, FR-3.2, FR-8.6, NFR-R1 (Reproducibility)

---

### Story 6.3: Implement Manifest (Run Metadata)

As a user,
I want run metadata captured for reproducibility and tracking,
So that I can understand what was run, when, and with what configuration.

**Acceptance Criteria:**

- **Given** a run completes
  **When** manifest.json is written to run directory
  **Then** it contains:
  - timestamp (ISO 8601 format - run start time)
  - config_hash (SHA256 hash of all configs for reproducibility)
  - scenario_count (number of scenarios executed)
  - variant_count (number of variants/agents tested)
  - judge_count (number of judges applied)
  - processor_type (e.g., "prompt_input", "closedbox_input")
  - status ("completed", "failed", or "partial")
  - duration_seconds (total run time)
  - completed_count (scenarios successfully completed)
  - failed_count (scenarios that failed)

- **Given** two runs with same config and scenarios
  **When** config_hash is compared
  **Then** they match (reproducibility verification)

- **Given** manifest.json exists in run directory
  **When** it's examined
  **Then** all counts match the actual results in results_raw.jsonl and results_judged.jsonl

**Implementation Notes:**
- Created after execution and judging completes
- Config hash: SHA256(agents.json + eval_config.json + async_config.json + scenarios.json)
- Status is set based on whether all scenarios completed successfully
- File written to: `run_dir / "manifest.json"`
- Use Pydantic model for validation

**Related Requirements:** FR-3.2, FR-8.5, NFR-R1 (Reproducibility)

---

### Story 6.3.1: Generate Configuration Hash for Reproducibility

As a developer,
I want configuration hashes computed for reproducibility verification,
So that identical configs are easily recognized.

**Acceptance Criteria:**

- **Given** evaluation configs exist
  **When** hash is computed
  **Then** it's computed from:
  - agents.json contents
  - eval_config.json contents
  - async_config.json contents
  - scenarios.json (or .csv) contents
  (in consistent order)

- **Given** configs are identical
  **When** hash is computed for two runs
  **Then** both hashes match exactly

- **Given** a config file changes (even whitespace)
  **When** hash is recomputed
  **Then** the hash differs

- **Given** config hash is saved in manifest.json
  **When** reproducibility is verified
  **Then** I can compare hashes to confirm identical configurations

**Implementation Notes:**
- Use hashlib.sha256()
- Hash the JSON content in canonical form (sorted keys)
- Include file modification times if desired for additional uniqueness
- Store in manifest.json as "config_hash" field

**Related Requirements:** NFR-R1 (Reproducibility), FR-8.5

---

### Story 6.4: Implement Run History Tracking

As a user,
I want to list all completed runs with summaries,
So that I can track evaluation history and compare variants over time.

**Acceptance Criteria:**

- **Given** multiple runs have completed
  **When** `gavel oneshot list` is invoked
  **Then** all runs are displayed with: timestamp, eval name, variant count, best variant

- **Given** `gavel oneshot list --eval <name>` is invoked
  **When** filtered
  **Then** only runs for that evaluation are shown

- **Given** runs exist from different dates
  **When** `gavel oneshot list --after 2025-12-01` is invoked
  **Then** only runs after that date are shown

- **Given** run history is large
  **When** list is generated
  **Then** output is readable (pagination or summary format)

**Related Requirements:** FR-3.4, FR-7.6

---

### Story 6.5: Implement Milestone Marking

As a user,
I want to mark important runs as milestones,
So that baseline and production-ready evaluations are preserved and easy to find.

**Acceptance Criteria:**

- **Given** a completed run
  **When** `gavel oneshot milestone --run <run-id> --comment "Baseline for v1.0"` is invoked
  **Then** the run is marked as a milestone

- **Given** the manifest.json is examined
  **When** the milestone flag is checked
  **Then** it's set to true with the comment and timestamp

- **Given** milestone runs are excluded from cleanup
  **When** `gavel clean` is run
  **Then** milestone runs are preserved (non-milestone old runs are deleted)

- **Given** `gavel oneshot list --milestones` is invoked
  **When** executed
  **Then** only milestone runs are displayed with their comments

**Related Requirements:** FR-3.7

---

### Story 6.6: Implement Run Cleanup

As a user,
I want old runs cleaned up automatically,
So that disk space is managed and only relevant runs are kept.

**Acceptance Criteria:**

- **Given** multiple runs exist, some older than 30 days
  **When** `gavel clean --older-than 30d` is invoked
  **Then** runs older than 30 days are deleted (except milestones)

- **Given** a specific run should be deleted
  **When** `gavel clean --run <run-id>` is invoked
  **Then** that run is deleted

- **Given** cleanup is about to run
  **When** confirmation is requested
  **Then** the user can review what will be deleted before confirming

**Related Requirements:** FR-8.7

---

### Story 6.7: Implement Run Archive & Export

As a user,
I want to export runs for long-term storage or sharing,
So that important evaluations can be preserved and reproduced.

**Acceptance Criteria:**

- **Given** a completed run
  **When** `gavel export --run <run-id> --format zip` is invoked
  **Then** the entire run (configs, scenarios, results, artifacts) is exported as run-<id>.zip

- **Given** the zip file is extracted on another machine
  **When** `gavel import --file run-<id>.zip` is invoked
  **Then** the run is re-imported with all artifacts intact

- **Given** imported run exists
  **When** examined
  **Then** it can be used for re-judging, re-reporting, or analysis

**Related Requirements:** FR-3.5

---

### Story 6.8: Implement RunContext Programmatic API

As a developer,
I want to access run artifacts programmatically (future SDK),
So that custom analysis scripts and notebooks can load and analyze results.

**Acceptance Criteria:**

- **Given** RunContext API exists
  **When** `run = await Run.load(run_id)` is called
  **Then** the run object is loaded with all artifacts

- **Given** the run object is loaded
  **When** `run.artifacts['results']` is accessed
  **Then** results.jsonl is loaded and available as list of results

- **Given** telemetry artifacts exist
  **When** `run.artifacts['telemetry']` is accessed
  **Then** telemetry.jsonl is loaded and available for analysis

- **Given** run metadata is needed
  **When** `run.metadata` is accessed
  **Then** manifest.json data is available

**Related Requirements:** FR-3.6

---

## Epic 7: Observability & Quality

**Epic Goal:** Provide comprehensive observability, error handling, health checks, and quality gates.

**User Stories:**

### Story 7.1: Implement Telemetry Collection & Storage with ISO 8601 Format

As a developer,
I want complete execution telemetry captured in OpenTelemetry format with proper timestamps,
So that performance, debugging, and observability are built-in.

**Updated Requirements (2026-01-01):**

Telemetry format updated to use ISO 8601 timestamps for consistency with other run artifacts.

**Acceptance Criteria:**

- **Given** an evaluation runs
  **When** processors, judges, and in-situ calls execute
  **Then** OT spans are emitted to centralized receiver

- **Given** all spans are collected
  **When** evaluation completes
  **Then** they're exported to telemetry.jsonl in JSONL format

- **Given** telemetry.jsonl is examined
  **When** individual spans are inspected
  **Then** each span has: trace_id, span_id, parent_span_id, name, timestamps, duration, attributes, status

- **Given** span timestamps are recorded
  **When** telemetry.jsonl is examined
  **Then** start_time_iso and end_time_iso use ISO 8601 format (e.g., 2026-01-01T23:29:10.123456Z)

- **Given** telemetry is enabled
  **When** evaluation runs
  **Then** <5% overhead is added (performance impact is minimal)

**Telemetry Format (ISO 8601):**
```json
{
  "trace_id": "uuid",
  "span_id": "uuid",
  "parent_span_id": "uuid or null",
  "name": "processor.execute",
  "start_time_iso": "2026-01-01T23:29:10.123456Z",
  "end_time_iso": "2026-01-01T23:29:12.456789Z",
  "duration_ms": 2333,
  "status": "ok|error",
  "attributes": {
    "processor.type": "prompt_input",
    "scenario.id": "scenario-5",
    "variant.id": "variant-1"
  }
}
```

**Implementation Notes:**
- Use datetime.now(timezone.utc).isoformat() for timestamp consistency
- Timestamps include microseconds (6 decimal places)
- All timestamps are in UTC timezone
- Consistent format with results_raw.jsonl and manifest.json timestamps

**Related Requirements:** FR-2.4, FR-8.3, Decision 9, NFR-R1 (Reproducibility)

---

### Story 7.2: Implement Run Metadata Telemetry

As a user,
I want execution metrics captured (timing, token counts, etc.),
So that performance can be analyzed and optimized.

**Acceptance Criteria:**

- **Given** an evaluation completes
  **When** run_metadata.json is examined
  **Then** it contains:
  - Total duration
  - Mean/median/min/max/std processing time per scenario
  - Total LLM calls and tokens
  - Completed/failed scenario count
  - Retry statistics

- **Given** the metadata is available
  **When** reports are generated
  **Then** performance metrics are included and formatted clearly

**run_metadata.json Schema:**
```json
{
  "total_duration_seconds": 120,
  "scenario_timing": {
    "count": 10,
    "mean_ms": 2500,
    "median_ms": 2400,
    "min_ms": 1800,
    "max_ms": 3200,
    "std_ms": 450
  },
  "llm_calls": {
    "total": 40,
    "by_model": {
      "claude-3-5-sonnet": 20,
      "gpt-4": 20
    },
    "tokens": {
      "prompt_total": 5000,
      "completion_total": 2000
    }
  },
  "execution": {
    "completed": 10,
    "failed": 0,
    "retries": 2
  }
}
```

**Related Requirements:** FR-9.5, FR-9.8

---

### Story 7.3: Implement Error Categorization & Handling

As a developer,
I want consistent error categorization and recovery guidance,
So that users understand failures and know how to fix them.

**Acceptance Criteria:**

- **Given** an error occurs during evaluation
  **When** it's caught
  **Then** it's categorized as: Configuration, Validation, Execution, or System

- **Given** an error is Configuration
  **When** raised
  **Then** the message includes: what config is wrong + how to fix

- **Given** an error is Execution (transient)
  **When** raised
  **Then** automatic retries are attempted based on config

- **Given** an error is Execution (non-transient)
  **When** raised
  **Then** it fails immediately with recovery guidance

- **Given** debug mode is enabled
  **When** an error occurs
  **Then** full stack trace and context are logged

**Error Hierarchy:**
```python
GavelError (base)
├── ConfigError
├── ValidationError
├── ProcessorError
├── JudgeError
├── StorageError
└── TelemetryError
```

**Error Message Format (Required):**
```
<ErrorType>: <What happened> - <Recovery step>
```

**Related Requirements:** FR-9.1, FR-9.2, Decision 7

---

### Story 7.4: Implement Debug Mode

As a developer,
I want to debug evaluation issues with verbose logging,
So that troubleshooting problems is efficient and clear.

**Acceptance Criteria:**

- **Given** `gavel oneshot run --eval <name> --debug` is invoked
  **When** execution runs
  **Then** DEBUG level logs are output

- **Given** debug mode is enabled
  **When** LLM calls are made
  **Then** request/response details are logged (with secrets masked)

- **Given** debug mode is enabled
  **When** errors occur
  **Then** full stack traces are included

- **Given** telemetry is enabled
  **When** debug mode runs
  **Then** span details are logged as they're emitted

**Related Requirements:** FR-9.3, FR-9.4

---

### Story 7.5: Implement Health Checks & Diagnostics

As a user,
I want to verify the system is working,
So that setup issues are caught early.

**Acceptance Criteria:**

- **Given** `gavel health` is invoked
  **When** executed
  **Then** it checks:
  - LLM API keys are set (environment)
  - LLM providers are reachable (quick test call if possible)
  - Disk space is available
  - Python version is compatible

- **Given** `gavel diagnose` is invoked
  **When** executed
  **Then** it collects:
  - System info (OS, Python version, dependencies)
  - Configuration status (eval-root exists, etc.)
  - Recent logs
  - And outputs a diagnostic report

**Related Requirements:** FR-9.7

---

### Story 7.6: Implement Pre-Execution Validation

As a developer,
I want configuration and scenario validation before execution starts,
So that errors are caught early and clearly.

**Acceptance Criteria:**

- **Given** a config file is missing required fields
  **When** validation runs (before execution)
  **Then** ValidationError is raised with clear message

- **Given** a scenario has invalid format
  **When** validation runs
  **Then** ValidationError explains the issue

- **Given** judge configuration is invalid
  **When** validation runs
  **Then** JudgeError indicates what's wrong

- **Given** all validation passes
  **When** execution starts
  **Then** no configuration errors can occur mid-run

**Related Requirements:** FR-9.6

---

### Story 7.7: Implement Structured Logging to gavel.log

As a developer,
I want all logs written to run-specific log file,
So that execution details are available for debugging and auditing.

**Acceptance Criteria:**

- **Given** an evaluation runs
  **When** execution completes
  **Then** gavel.log exists in run directory with all logs

- **Given** gavel.log is examined
  **When** entries are checked
  **Then** they follow standard format:
  `"%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"`

- **Given** errors occur during evaluation
  **When** gavel.log is examined
  **Then** error stack traces are logged

**Related Requirements:** FR-9.4

---

### Story 7.8: Implement CI/CD Integration Support

As a DevOps engineer,
I want gavel to integrate seamlessly with CI/CD pipelines,
So that automated testing is straightforward.

**Acceptance Criteria:**

- **Given** `gavel oneshot run --eval <name>` is invoked in CI
  **When** execution completes
  **Then** exit code is: 0 (success), 1 (error), 2 (eval failed quality gate)

- **Given** `--output json` is specified
  **When** command completes
  **Then** structured JSON output is printed (parseable by scripts)

- **Given** a quality gate is defined (e.g., "best variant score >= 7")
  **When** results don't meet the gate
  **Then** exit code 2 is returned (evaluation failed)

- **Given** CI runs gavel
  **When** artifacts are generated
  **Then** they're stored in standard location (not hardcoded paths)

**Related Requirements:** FR-7.7, NFR-I1

---

## Next Steps

Once all epics are decomposed into stories, each story will be:
1. Reviewed and validated for completeness
2. Assigned to development sprints
3. Implemented with tests and validation
4. Verified against acceptance criteria
5. Marked complete when all criteria are met

All stories follow the project's consistency rules and architectural patterns documented in the architecture guide.

