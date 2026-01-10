# Tech Spec: Refactor OneShot Run Method for Maintainability

**Story:** Epic 3, Story 3.9
**Created:** 2026-01-06
**Status:** Ready for Implementation

---

## Overview

The current `src/gavel_ai/cli/workflows/oneshot.py:run()` method is a 400+ line monolithic function with mixed concerns: config loading, validation, processor instantiation, scenario execution, judging, results export, report generation, and telemetry management.

This spec proposes refactoring into a clean, testable architecture using:
- **EvalContext**: Immutable evaluation metadata (configs, scenarios, prompts)
- **RunContext**: Mutable run state (step outputs, artifacts)
- **Step ABC**: Abstract base class for workflow phases
- **Concrete steps**: Validator, ScenarioProcessor, JudgeRunner, ReportRunner

This design isolates concerns, improves testability, and enables future workflow variants without rewriting the orchestration loop.

---

## Current State Problem

### Issues with Current Implementation

1. **Monolithic function** (400+ lines)
   - All logic in single `run()` method
   - Hard to test individual phases
   - Difficult to extract common patterns

2. **Loose data flow**
   - Dozens of local variables
   - No clear input/output contracts between phases
   - Scenario filtering placeholder not implemented

3. **Brittle phase transitions**
   - Each phase loads/saves its own artifacts
   - No structured error recovery
   - Difficult to skip or re-order steps

4. **Type safety gaps**
   - No explicit contracts for step inputs/outputs
   - Easy to pass wrong data types between phases

---

## Proposed Architecture

**NOTE:** This architecture follows the **Storage Abstraction Pattern** as defined in `storage-abstraction-specification.md`. See that document for the complete 3-layer architecture design (Backend → DataSource → Context).

### 1. EvalContext (Storage Abstraction)

**Purpose:** Provide read-only access to evaluation configuration via DataSource abstractions.

**Design Philosophy:**
- EvalContext properties return **DataSource objects**, not data directly
- Steps call `.read()` on DataSources to access data
- Enables testing with InMemoryStorageBackend
- Supports multiple storage backends without changing step code

```python
class LocalFileSystemEvalContext:
    """
    Local filesystem evaluation context implementation.

    Provides lazy-loaded DataSource objects for evaluation configuration.
    Steps access data by calling .read() on the data sources.
    """

    def __init__(self, eval_name: str, eval_root: Path = Path(".gavel/evaluations")):
        """
        Initialize evaluation context.

        Args:
            eval_name: Name of the evaluation
            eval_root: Root directory for evaluations (default: .gavel/evaluations)
        """
        self._eval_name: str = eval_name
        self._eval_root: Path = eval_root

        # Initialize storage backend
        self._storage = LocalStorageBackend(self._eval_root / eval_name)

        # Lazy-loaded data sources
        self._eval_config_source: Optional[StructDataSource[EvalConfig]] = None
        self._agents_source: Optional[StructDataSource[AgentsConfig]] = None
        self._scenarios_source: Optional[RecordDataSource[Scenario]] = None

        # Caches
        self._prompt_cache: Dict[str, str] = {}

    @property
    def eval_name(self) -> str:
        """Evaluation name."""
        return self._eval_name

    @property
    def eval_root(self) -> Path:
        """Evaluation root directory."""
        return self._eval_root

    @property
    def eval_dir(self) -> Path:
        """Evaluation directory path."""
        return self._eval_root / self._eval_name

    @property
    def config_dir(self) -> Path:
        """Configuration directory path."""
        return self.eval_dir / "config"

    @property
    def eval_config(self) -> StructDataSource[EvalConfig]:
        """
        Evaluation configuration data source (config/eval_config.json).

        Returns DataSource - steps must call .read() to get data.
        Lazy-loaded on first access.
        """
        if self._eval_config_source is None:
            self._eval_config_source = StructDataSource(
                self._storage,
                "config/eval_config.json",
                schema=EvalConfig
            )
        return self._eval_config_source

    @property
    def agents(self) -> StructDataSource[AgentsConfig]:
        """
        Agents configuration data source (config/agents.json).

        Returns DataSource - steps must call .read() to get data.
        Lazy-loaded on first access.
        """
        if self._agents_source is None:
            self._agents_source = StructDataSource(
                self._storage,
                "config/agents.json",
                schema=AgentsConfig
            )
        return self._agents_source

    @property
    def scenarios(self) -> RecordDataSource[Scenario]:
        """
        Scenarios data source (data/scenarios.json or .csv).

        Returns DataSource - steps can:
        - Call .read() to load all scenarios into memory
        - Call .iter() to stream scenarios one at a time
        Lazy-loaded on first access.
        """
        if self._scenarios_source is None:
            # Auto-detect format from file extension
            scenarios_path = "data/scenarios.json"
            if not (self.eval_dir / scenarios_path).exists():
                scenarios_path = "data/scenarios.csv"

            self._scenarios_source = RecordDataSource(
                self._storage,
                scenarios_path,
                schema=Scenario
            )
        return self._scenarios_source

    def get_prompt(self, prompt_ref: str) -> str:
        """
        Get prompt template content (cached).

        Args:
            prompt_ref: Prompt reference in format "name:version" or "name:latest"

        Returns:
            Prompt template text with {{variable}} placeholders

        Raises:
            FileNotFoundError: If prompt file or version not found
        """
        if prompt_ref not in self._prompt_cache:
            # Parse prompt_ref: "name:version"
            name, version = prompt_ref.split(":")

            # Read TOML file
            prompt_source = StructDataSource(
                self._storage,
                f"config/prompts/{name}.toml"
            )
            prompt_data = prompt_source.read()  # dict

            # Get specific version or latest
            if version == "latest":
                # Get highest version number
                versions = [k for k in prompt_data.keys() if k.startswith("v")]
                version = max(versions, key=lambda v: int(v[1:]))

            if version not in prompt_data:
                raise KeyError(f"Version {version} not found in prompt {name}")

            self._prompt_cache[prompt_ref] = prompt_data[version]

        return self._prompt_cache[prompt_ref]
```

**Key Properties:**
- **DataSource abstraction**: Properties return DataSource objects, not data
- **Lazy-loading**: DataSources only created when accessed
- **Caching**: Prompts cached to avoid repeated disk I/O
- **Storage backend**: Uses LocalStorageBackend for file operations
- **Single source of truth**: All config accesses go through EvalContext

**Usage in Steps:**
```python
# Steps access data by calling .read()
eval_config = run_ctx.eval_ctx.eval_config.read()  # EvalConfig instance
agents = run_ctx.eval_ctx.agents.read()  # AgentsConfig instance
scenarios = run_ctx.eval_ctx.scenarios.read()  # List[Scenario]

# Or stream scenarios efficiently
for scenario in run_ctx.eval_ctx.scenarios.iter():
    process(scenario)
```

---

### 2. RunContext (Storage Abstraction)

**Purpose:** Provide read/write access to run artifacts via DataSource abstractions.

**Design Philosophy:**
- RunContext exposes **DataSource objects** for artifacts, not in-memory data
- Steps write results immediately via `.append()` or `.write()` on DataSources
- **Write-through architecture**: Data persisted immediately, no separate save step needed
- Safer than accumulate-then-save (data persisted even if later steps fail)
- More memory-efficient for large runs (don't accumulate all results in memory)

```python
class LocalRunContext:
    """
    Local filesystem run context implementation.

    Provides DataSource objects for run artifacts. Steps write data immediately
    to storage via the data sources.
    """

    def __init__(
        self,
        eval_ctx: LocalFileSystemEvalContext,
        base_dir: Path = Path(".gavel/runs"),
        run_id: Optional[str] = None
    ):
        """
        Initialize run context.

        Args:
            eval_ctx: Evaluation context with configuration
            base_dir: Base directory for runs (default: .gavel/runs)
            run_id: Run identifier (generated if not provided)
        """
        # Reference to eval context
        self._eval_ctx = eval_ctx

        # Generate run_id if not provided
        if run_id is None:
            from datetime import datetime
            run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        self._run_id = run_id
        self._base_dir = base_dir

        # Initialize storage backend
        self._storage = LocalStorageBackend(base_dir)

        # Initialize all artifact data sources
        self._init_artifacts()

        # Configure run-specific logger
        self._configure_logger()

        # Snapshot eval config for reproducibility
        self.snapshot_run_config()

    @property
    def eval_ctx(self) -> LocalFileSystemEvalContext:
        """Access to evaluation configuration."""
        return self._eval_ctx

    @property
    def run_id(self) -> str:
        """Run identifier."""
        return self._run_id

    @property
    def run_dir(self) -> Path:
        """Run directory path."""
        return self._base_dir / self._run_id

    def _init_artifacts(self) -> None:
        """
        Initialize artifact data sources for local filesystem storage.

        Each artifact is exposed as a DataSource property that steps
        can write to immediately.
        """
        # Raw results - JSONL with schema validation
        self._results_raw = RecordDataSource(
            self._storage,
            f"{self._run_id}/results_raw.jsonl",
            format="jsonl",
            schema=OutputRecord
        )

        # Judged results - JSONL with schema validation
        self._results_judged = RecordDataSource(
            self._storage,
            f"{self._run_id}/results_judged.jsonl",
            format="jsonl",
            schema=JudgedRecord
        )

        # Telemetry - JSONL with schema validation
        self._telemetry = RecordDataSource(
            self._storage,
            f"{self._run_id}/telemetry.jsonl",
            format="jsonl",
            schema=TelemetrySpan
        )

        # Run metadata - JSON with schema validation
        self._run_metadata = StructDataSource(
            self._storage,
            f"{self._run_id}/run_metadata.json",
            format="json",
            schema=RunMetadata
        )

        # Reports - multiple formats (html, md, pdf)
        self._reports = MultiFormatDataSource(
            self._storage,
            f"{self._run_id}",  # Base directory
            "report"  # Base filename
        )

    def _configure_logger(self) -> None:
        """Configure run-specific logger for local filesystem."""
        import logging
        from logging.handlers import RotatingFileHandler

        log_file = self._base_dir / self._run_id / "run.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
            )
        )

        # Create run-specific logger
        self._run_logger = logging.getLogger(f"gavel_ai.{self._run_id}")
        self._run_logger.addHandler(handler)
        self._run_logger.setLevel(logging.INFO)
        self._run_logger.propagate = False

    def snapshot_run_config(self) -> None:
        """
        Copy eval configs to .config/ subdirectory for reproducibility.

        This ensures the exact configuration used for this run is preserved,
        even if the eval config is later modified.
        """
        config_snapshot_dir = f"{self._run_id}/.config"

        # Copy eval_config.json
        eval_config_content = self._eval_ctx.eval_config.read()
        eval_config_snapshot = StructDataSource(
            self._storage,
            f"{config_snapshot_dir}/eval_config.json",
            format="json"
        )
        eval_config_snapshot.write(eval_config_content)

        # Copy agents.json
        agents_content = self._eval_ctx.agents.read()
        agents_snapshot = StructDataSource(
            self._storage,
            f"{config_snapshot_dir}/agents.json",
            format="json"
        )
        agents_snapshot.write(agents_content)

        # Copy scenarios
        scenarios_content = self._eval_ctx.scenarios.read()
        scenarios_snapshot = RecordDataSource(
            self._storage,
            f"{config_snapshot_dir}/scenarios.json",
            format="json"
        )
        scenarios_snapshot.write(scenarios_content)

    # Artifact properties - expose DataSources to steps
    @property
    def results_raw(self) -> RecordDataSource[OutputRecord]:
        """
        Raw execution results data source.

        Steps write results via: run_ctx.results_raw.append(record)
        """
        return self._results_raw

    @property
    def results_judged(self) -> RecordDataSource[JudgedRecord]:
        """
        Judged results data source.

        Steps write results via: run_ctx.results_judged.append(record)
        """
        return self._results_judged

    @property
    def telemetry(self) -> RecordDataSource[TelemetrySpan]:
        """
        Telemetry spans data source (REQUIRED - source of truth for metrics).

        Steps write spans via: run_ctx.telemetry.append(span)
        """
        return self._telemetry

    @property
    def run_metadata(self) -> StructDataSource[RunMetadata]:
        """
        Run metadata summary data source.

        Reporter writes metadata via: run_ctx.run_metadata.write(metadata)
        """
        return self._run_metadata

    @property
    def reports(self) -> MultiFormatDataSource:
        """
        Reports in multiple formats data source.

        Reporter writes via: run_ctx.reports.write(html, "html")
        """
        return self._reports

    @property
    def run_logger(self) -> logging.Logger:
        """
        Run-specific logger configured with file handler.

        Steps use for logging: run_ctx.run_logger.info("message")
        """
        return self._run_logger
```

**Key Properties:**
- **DataSource abstraction**: Properties expose DataSources for artifacts
- **Write-through persistence**: Data written immediately via `.append()` or `.write()`
- **No LocalFilesystemRun object**: Replaced by StorageBackend + DataSources
- **Run-specific logger**: Automatically configured with rotating file handler
- **Config snapshot**: Captures exact configs used for reproducibility

**Usage in Steps:**
```python
# Steps write data immediately to storage
for scenario in scenarios:
    result = process_scenario(scenario)
    # Write immediately - no accumulation in memory
    run_ctx.results_raw.append(result)

    # Log to run-specific log file
    run_ctx.run_logger.info(f"Processed scenario: {scenario.id}")

# Reporter generates and saves reports
html = generate_html_report(...)
run_ctx.reports.write(html, "html")
run_ctx.reports.write(markdown, "md")

# Save run metadata
metadata = compute_metadata(...)
run_ctx.run_metadata.write(metadata)
```

---

### 3. Step ABC

**Purpose:** Abstract base class for workflow steps. Enables isolation and testability.

```python
from abc import ABC, abstractmethod
from enum import Enum

class StepPhase(Enum):
    """Workflow step phases in execution order."""
    VALIDATION = "validation"
    SCENARIO_PROCESSING = "scenario_processing"
    JUDGING = "judging"
    REPORTING = "reporting"

class Step(ABC):
    """
    Abstract step in the OneShot workflow.

    Steps are isolated units of execution that:
    - Read inputs from RunContext.eval_ctx (via DataSources)
    - Write outputs to RunContext artifact DataSources
    - Log progress using run_ctx.run_logger
    - Use tracer for observability
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize step.

        Args:
            logger: Logger for step execution (class-level logging)
        """
        self.logger: logging.Logger = logger
        self.tracer = get_tracer(__name__)  # Get tracer from telemetry module

    @property
    @abstractmethod
    def phase(self) -> StepPhase:
        """Which phase of the workflow this step executes in."""
        pass

    @abstractmethod
    async def execute(self, context: RunContext) -> None:
        """
        Execute the step.

        Args:
            context: RunContext for reading inputs and writing outputs

        Raises:
            ValidationError: On validation failures (terminal by default)
            ConfigError: On configuration issues (terminal by default)
            Exception: Other errors propagate as terminal by default

        Implementation notes:
        - Read inputs via: context.eval_ctx.eval_config.read()
        - Write outputs via: context.results_raw.append(record)
        - Log progress using: context.run_logger.info("message")
        - Use tracer.start_as_current_span() for observability
        """
        pass

    async def safe_execute(self, context: RunContext) -> bool:
        """
        Execute with error handling wrapper.

        Called by workflow orchestrator. Public method (no underscore).

        Returns:
            True if successful, False on terminal error
        """
        try:
            await self.execute(context)
            return True
        except (ValidationError, ConfigError) as e:
            self.logger.error(f"{self.phase.value} failed: {e}", exc_info=True)
            context.run_logger.error(f"{self.phase.value} failed: {e}", exc_info=True)
            return False
        except Exception as e:
            self.logger.error(f"{self.phase.value} failed with unexpected error: {e}", exc_info=True)
            context.run_logger.error(f"{self.phase.value} failed with unexpected error: {e}", exc_info=True)
            return False
```

**Key Design:**
- `execute()`: Pure implementation of step logic (reads/writes via DataSources)
- `safe_execute()`: Public wrapper with error handling (called by orchestrator)
- `phase`: Enum identifies which step (for logging/ordering)
- Logs errors to both class logger and run logger

---

### 4. Concrete Steps

#### 4a. ValidatorStep

**Responsibilities:**
- Validate eval_config loadable and valid
- Validate agents.json exists and has _models + subject_agent
- Validate scenarios list not empty
- Validate subject_agent model_id resolves in _models
- Validate prompts exist for referenced test_subjects

**Implementation notes:**
- Extracted from current run() lines 126-143
- Sets context.validation_result (for future non-terminal error handling)

#### 4b. ScenarioProcessorStep

**Responsibilities:**
- Instantiate processor (PromptInputProcessor or ClosedBoxInputProcessor) based on test_subject_type
- Convert scenarios to Input[]
- Execute via Executor with parallelism/error handling from async_config
- Store processor_results in context

**Implementation notes:**
- Extracted from current run() lines 173-244
- Handles both prompt_input and closedbox_input processors
- Sets context.processor_results for downstream judge/reporter

#### 4c. JudgeRunnerStep

**Responsibilities:**
- Extract judges from eval_config.test_subjects[]
- Resolve judge model IDs in agents_config
- If judges exist:
  - Prepare batch evaluations from scenarios + processor_results
  - Execute JudgeExecutor.execute_batch()
  - Store evaluation_results in context
- If no judges, set evaluation_results to []

**Implementation notes:**
- Extracted from current run() lines 247-318
- Idempotent: can skip if eval_config.judges is empty

#### 4d. ReportRunnerStep

**Responsibilities:**
- Export results_raw.jsonl (immutable processor outputs)
- Export results_judged.jsonl (judge evaluations)
- Generate manifest.json with config hash
- Compute and save run_metadata.json
- Generate report.html via OneShotReporter
- Save run via run_obj.save()

**Implementation notes:**
- Extracted from current run() lines 320-444
- Final step: commits all artifacts to filesystem
- Handles metadata collection and statistics computation

---

## Refactored Run Loop

**NOTE:** This workflow code should be in `src/gavel_ai/core/workflows/oneshot.py` (business logic tier), NOT in CLI tier. The CLI adapter (`src/gavel_ai/cli/commands/oneshot.py`) just instantiates contexts and calls the workflow.

```python
# src/gavel_ai/core/workflows/oneshot.py
class OneShotWorkflow:
    """
    Pure business logic orchestrator for OneShot evaluations.

    This class is completely CLI-agnostic and contains NO typer dependencies.
    """

    def __init__(self, eval_ctx: LocalFileSystemEvalContext, logger: logging.Logger):
        """
        Initialize OneShot workflow.

        Args:
            eval_ctx: Evaluation context with configs and scenarios
            logger: Logger for workflow execution (application-level)
        """
        self.eval_ctx = eval_ctx
        self.logger = logger

    async def execute(self) -> LocalRunContext:
        """
        Execute OneShot workflow - orchestrates validator → processor → judge → reporter steps.

        Returns:
            RunContext with all step outputs populated

        Raises:
            ConfigError: If configuration is invalid
            ValidationError: If validation fails
        """
        # Create run context - generates run_id and sets up artifacts
        run_ctx = LocalRunContext(
            eval_ctx=self.eval_ctx,
            base_dir=Path(".gavel/runs")
        )
        run_id = run_ctx.run_id

        # Run context automatically:
        # - Initializes artifact DataSources
        # - Configures run logger
        # - Snapshots configs for reproducibility

        # Configure telemetry (OpenTelemetry exporter)
        telemetry_path = configure_run_telemetry(
            run_id=run_id,
            eval_name=self.eval_ctx.eval_name,
            base_dir=".gavel/runs"
        )

        # Initialize metadata collector
        metadata_collector = get_metadata_collector()
        metadata_collector.record_run_start()

        try:
            self.logger.info(f"Running oneshot evaluation '{self.eval_ctx.eval_name}'")
            self.logger.info(f"Created run: {run_id}")

            # Create and execute steps
            await self._execute_steps(run_ctx)

            # Success logging
            self.logger.info(f"Evaluation '{self.eval_ctx.eval_name}' completed successfully")

            return run_ctx

        except ConfigError as e:
            run_ctx.run_logger.error(f"Configuration error: {e}", exc_info=True)
            self.logger.error(f"Configuration error: {e}", exc_info=True)
            raise

        except ValidationError as e:
            run_ctx.run_logger.error(f"Validation error: {e}", exc_info=True)
            self.logger.error(f"Validation error: {e}", exc_info=True)
            raise

        except Exception as e:
            run_ctx.run_logger.error(f"Execution error: {e}", exc_info=True)
            self.logger.error(f"Execution error: {e}", exc_info=True)
            raise

        finally:
            # Always reset telemetry and metadata after run completes
            reset_telemetry()
            reset_metadata_collector()

    async def _execute_steps(self, run_ctx: LocalRunContext) -> None:
        """
        Execute workflow steps in order.

        Args:
            run_ctx: Run context to populate with step outputs

        Raises:
            ConfigError: If step execution fails due to configuration
            ValidationError: If step execution fails due to validation
        """
        # Create steps (pass application logger for class-level logging)
        steps: List[Step] = [
            ValidatorStep(self.logger),
            ScenarioProcessorStep(self.logger),
            JudgeRunnerStep(self.logger),
            ReportRunnerStep(self.logger),
        ]

        # Execute steps in order
        for step in steps:
            self.logger.info(f"Running {step.phase.value}...")
            success: bool = await step.safe_execute(run_ctx)
            if not success:
                raise ProcessorError(f"Step {step.phase.value} failed")
            self.logger.info(f"Completed {step.phase.value}")


# src/gavel_ai/cli/commands/oneshot.py
@app.command()
async def run(
    eval_name: str = typer.Option(..., "--eval", help="Evaluation name"),
    scenarios: Optional[str] = typer.Option(None, "--scenarios", help="Scenario filter (e.g., 1-10)"),
) -> None:
    """CLI entry point for OneShot evaluation workflow."""
    app_logger = get_application_logger()
    app_logger.info(f"OneShot Evaluation '{eval_name}' started")

    # Create evaluation context
    eval_ctx = LocalFileSystemEvalContext(
        eval_name=eval_name,
        eval_root=Path(".gavel/evaluations")
    )

    try:
        # Call business logic (core tier)
        workflow = OneShotWorkflow(eval_ctx, app_logger)
        run_ctx = await workflow.execute()

        # Format output for CLI (presentation tier)
        typer.echo(f"✓ Created run: {run_ctx.run_id}")
        typer.echo("✓ Completed validation")
        typer.echo("✓ Completed scenario_processing")
        typer.echo("✓ Completed judging")
        typer.echo("✓ Completed reporting")

        # Print summary
        report_path = run_ctx.run_dir / "report.html"
        typer.echo("\n✅ Evaluation complete")
        typer.echo(f"   Run ID: {run_ctx.run_id}")
        typer.echo(f"   Report: {report_path.absolute()}")

    except (ConfigError, ValidationError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
```

**Key Changes from Original:**
1. **Separation of concerns**: Business logic in `OneShotWorkflow`, CLI formatting in CLI command
2. **No typer in workflow**: OneShotWorkflow is pure Python, can be called from API/script
3. **Concrete context classes**: `LocalFileSystemEvalContext`, `LocalRunContext`
4. **Run context auto-setup**: Config snapshot and logger configuration happen in `__init__`
5. **safe_execute()** (public): No underscore, called by workflow
6. **Steps use logger param**: Pass application logger for class-level logging
7. **No LocalFilesystemRun**: Replaced by DataSources managed by RunContext

---

## File Structure

```
src/gavel_ai/
├── core/
│   ├── adapters/                       # NEW: Storage abstraction layer
│   │   ├── __init__.py
│   │   ├── backends.py                 # StorageBackend implementations
│   │   └── data_sources.py             # DataSource implementations
│   ├── contexts.py                     # NEW: EvalContext and RunContext implementations
│   ├── workflows/                      # NEW: Workflow orchestrators
│   │   ├── __init__.py
│   │   ├── base.py                     # GavelWorkflow ABC (if needed)
│   │   └── oneshot.py                  # OneShotWorkflow (business logic)
│   └── steps/                          # NEW: Step implementations
│       ├── __init__.py
│       ├── base.py                     # Step ABC, StepPhase enum
│       ├── validator.py                # ValidatorStep
│       ├── scenario_processor.py       # ScenarioProcessorStep
│       ├── judge_runner.py             # JudgeRunnerStep
│       └── report_runner.py            # ReportRunnerStep
├── cli/
│   └── commands/
│       └── oneshot.py                  # REFACTOR: CLI adapter (calls OneShotWorkflow)
```

**Key Directories:**
- `core/adapters/`: Storage abstraction (backends + data sources)
- `core/contexts.py`: Context implementations (EvalContext, RunContext)
- `core/workflows/`: Workflow orchestrators (business logic, no CLI dependencies)
- `core/steps/`: Step implementations (use DataSources for I/O)
- `cli/commands/`: CLI adapters (presentation tier, typer commands)

---

## Acceptance Criteria

1. **Storage Abstraction Layer exists** (`core/adapters/`)
   - StorageBackend ABC and implementations (Local, Fsspec, InMemory)
   - DataSource types (StructDataSource, RecordDataSource, TextDataSource, MultiFormatDataSource)
   - All provide clean, type-safe APIs for data access

2. **EvalContext implementation exists** (`core/contexts.py`)
   - LocalFileSystemEvalContext with DataSource properties
   - Properties return DataSources, not data directly
   - Caches prompts for efficiency
   - Read-only access (immutable)

3. **RunContext implementation exists** (`core/contexts.py`)
   - LocalRunContext with artifact DataSource properties
   - Exposes: results_raw, results_judged, telemetry, run_metadata, reports, run_logger
   - Write-through architecture (immediate persistence)
   - Auto-configures run logger with file handler
   - Auto-snapshots configs for reproducibility

4. **Step ABC exists** (`core/steps/base.py`)
   - Abstract base class with phase property
   - execute(context) abstract method
   - safe_execute(context) public wrapper with error handling
   - StepPhase enum for workflow ordering

5. **Four concrete steps exist** (`core/steps/`)
   - ValidatorStep: validates configs via DataSources
   - ScenarioProcessorStep: processes scenarios, writes to results_raw
   - JudgeRunnerStep: runs judges, writes to results_judged
   - ReportRunnerStep: generates reports, writes metadata

6. **OneShotWorkflow exists** (`core/workflows/oneshot.py`)
   - Pure business logic orchestrator (no typer dependencies)
   - Takes EvalContext and logger in constructor
   - execute() method creates RunContext and orchestrates steps
   - Returns RunContext for inspection

7. **CLI adapter updated** (`cli/commands/oneshot.py`)
   - Instantiates LocalFileSystemEvalContext
   - Creates OneShotWorkflow and calls execute()
   - Formats output for CLI (presentation tier)
   - No business logic in CLI layer

8. **All existing tests pass**
   - Integration tests verify end-to-end execution
   - All 387+ existing tests still pass

9. **New unit tests added**
   - Test each Step in isolation with InMemoryStorageBackend
   - Test EvalContext lazy-loading and caching
   - Test RunContext artifact initialization
   - Test workflow orchestration
   - Test EvalContext lazy-loading
   - Test RunContext state management
   - Test step error handling

---

## Testing Strategy

### Unit Tests (per step)

```python
# tests/unit/test_validator_step.py
async def test_validator_step_validates_eval_config(mock_eval_context, mock_run_context):
    step = ValidatorStep(logger, tracer)
    await step.execute(mock_run_context)
    assert mock_run_context.validation_result is not None

# tests/unit/test_scenario_processor_step.py
async def test_scenario_processor_step_executes_scenarios(mock_eval_context, mock_run_context):
    step = ScenarioProcessorStep(logger, tracer)
    await step.execute(mock_run_context)
    assert mock_run_context.processor_results is not None
    assert len(mock_run_context.processor_results) == len(mock_eval_context.scenarios)
```

### Integration Tests

```python
# tests/integration/test_oneshot_run_refactored.py
async def test_end_to_end_evaluation_with_steps():
    """Verify complete run using new Step architecture."""
    eval_context = EvalContext("test_eval")
    run_context = RunContext(eval_context, "run-test")

    steps = [
        ValidatorStep(...),
        ScenarioProcessorStep(...),
        JudgeRunnerStep(...),
        ReportRunnerStep(...),
    ]

    for step in steps:
        success = await step._safe_execute(run_context)
        assert success

    assert run_context.processor_results is not None
    assert run_context.report_content is not None
```

---

## Key Design Decisions

1. **Step phases hardcoded** (not configurable)
   - Order: validator → processor → judge → reporter
   - Simplifies implementation, aligns with current flow
   - Future: can make configurable for Conversational/Autotune workflows

2. **Fail-fast error handling** (default)
   - Any step exception halts the run
   - Simpler than supporting "non-terminal" errors in v1
   - Can extend later with Step.skip_on_error flag

3. **EvalContext immutable**
   - No setters
   - Prevents accidental mutations
   - Safe for concurrent step reads (if parallelized future)

4. **RunContext property-based**
   - Each step output is a property
   - Type-safe: strongly-typed output contracts
   - Easy to extend: add new property for new step output

---

## Migration Path

1. Create new Step classes in `src/gavel_ai/core/steps/`
2. Create EvalContext and RunContext in `src/gavel_ai/core/workflows.py`
3. Extract logic from run() into each Step.execute()
4. Refactor run() to use new architecture
5. Add unit tests for each Step
6. Verify integration tests still pass
7. Mark old code (if any extracted methods) as internal

---

## Future Extensions

1. **Scenario filtering** (implement --scenarios 1-5 parameter)
2. **Step customization** (allow skipping judge or report step)
3. **Non-terminal errors** (Step.non_terminal_errors flag)
4. **Workflow variants** (Conversational, Autotune inherit from Step)
5. **Parallel step execution** (if steps become independent)
