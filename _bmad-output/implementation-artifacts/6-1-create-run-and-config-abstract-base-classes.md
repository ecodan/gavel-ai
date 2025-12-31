# Story 6.1: Create Run and Config Abstract Base Classes

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want pluggable storage abstractions,
So that storage can be changed (filesystem → database → S3) without modifying business logic.

## Acceptance Criteria

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

## Tasks / Subtasks

- [ ] Create StorageError exception in src/gavel_ai/core/exceptions.py (AC: All)
  - [ ] Inherit from GavelError
  - [ ] Add comprehensive docstring with use cases

- [ ] Create ArtifactRef model in src/gavel_ai/core/models.py (AC: 1)
  - [ ] Define path, type, size fields
  - [ ] Use Pydantic BaseModel with ConfigDict(extra="ignore")

- [ ] Create Run ABC in src/gavel_ai/storage/base.py (AC: 1)
  - [ ] Define async save() abstract method
  - [ ] Define async load(run_id) static abstract method
  - [ ] Define artifacts property returning Dict[str, ArtifactRef]
  - [ ] Add __init__ with run_id, metadata fields
  - [ ] Include OpenTelemetry tracer initialization
  - [ ] Reference Architecture Decision 8 in docstring

- [ ] Create Config ABC in src/gavel_ai/storage/base.py (AC: 2)
  - [ ] Define async load() abstract method
  - [ ] Define async save() abstract method
  - [ ] Add __init__ with config_path field
  - [ ] Include OpenTelemetry tracer initialization
  - [ ] Reference Architecture Decision 8 in docstring

- [ ] Create Prompt ABC in src/gavel_ai/storage/base.py (AC: 3)
  - [ ] Define async load(version) abstract method
  - [ ] Define async save(version, content) abstract method
  - [ ] Add __init__ with prompt_name, prompt_path fields
  - [ ] Include OpenTelemetry tracer initialization
  - [ ] Reference Architecture Decision 8 in docstring

- [ ] Update exports in src/gavel_ai/storage/__init__.py (AC: All)
  - [ ] Export Run, Config, Prompt ABCs
  - [ ] Export ArtifactRef model
  - [ ] Export StorageError

- [ ] Write comprehensive tests in tests/unit/storage/test_base.py (AC: All)
  - [ ] Test Run ABC instantiation and interface
  - [ ] Test Config ABC instantiation and interface
  - [ ] Test Prompt ABC instantiation and interface
  - [ ] Test ArtifactRef model validation
  - [ ] Create concrete test implementations to verify abstract methods
  - [ ] Achieve 70%+ coverage on non-trivial code

## Dev Notes

### Architecture Context

This story implements **Storage Abstraction Layer** per Architecture Decision 8, establishing the foundation for pluggable storage implementations.

**Key Architectural Principles (Decision 8):**
- Domain-driven design: Each object knows how to persist/load itself
- v1: Local filesystem implementations (Story 6.2)
- v2+: Database, S3, Experiment Tracking implementations
- Clean interfaces enable swapping storage without changing business logic

**Epic 6 Context:**
This is the foundation story for Epic 6 (Run Management & Artifact Storage). All subsequent stories (6.2-6.8) depend on these abstractions:
- Story 6.2: LocalFilesystemRun implements Run ABC
- Story 6.3: Manifest metadata uses Run.artifacts
- Story 6.4-6.8: Run history, milestones, cleanup, archive all use Run interface

### Dependencies on Previous Stories

**CRITICAL: These abstractions are NEW domain concepts. No prior stories implement storage.**

**From Epic 4 (Judging & Result Evaluation):**
- Results storage in Story 4.6 currently writes directly to filesystem
- Future: Will be refactored to use Run.save() for artifact persistence

**From Epic 5 (Reporting):**
- Reporter (Story 5.1) currently takes generic `run: Any` parameter
- Future: Will be typed to use Run ABC for proper type hints

### Implementation Patterns

**Run ABC Structure** (per Decision 8):
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from gavel_ai.telemetry import get_tracer
from gavel_ai.core.models import ArtifactRef

class Run(ABC):
    """
    Abstract base class for run storage.

    Per Architecture Decision 8: Domain-driven storage abstraction.
    Each Run implementation knows how to persist and load its own artifacts.

    v1 Implementations: LocalFilesystemRun (Story 6.2)
    v2+ Implementations: DatabaseRun, S3Run, ExperimentTrackingRun
    """

    def __init__(self, run_id: str, metadata: Dict[str, Any]):
        """
        Initialize run with ID and metadata.

        Args:
            run_id: Unique identifier for this run (e.g., "run-20251230-120000")
            metadata: Run metadata (eval_name, timestamp, config_hash, etc.)
        """
        self.run_id = run_id
        self.metadata = metadata
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def save(self) -> str:
        """
        Persist run artifacts to storage.

        Returns:
            str: Storage location/path of saved run

        Raises:
            StorageError: On save failures
        """
        pass

    @staticmethod
    @abstractmethod
    async def load(run_id: str) -> "Run":
        """
        Load run from storage by ID.

        Args:
            run_id: Unique run identifier

        Returns:
            Run: Loaded run instance with all artifacts

        Raises:
            StorageError: If run not found or load fails
        """
        pass

    @property
    @abstractmethod
    def artifacts(self) -> Dict[str, ArtifactRef]:
        """
        Get dictionary of run artifacts.

        Returns:
            Dict mapping artifact names to ArtifactRef instances.

        Example:
            {
                "manifest": ArtifactRef(path="manifest.json", type="json", size=1024),
                "results": ArtifactRef(path="results.jsonl", type="jsonl", size=50000),
                "report": ArtifactRef(path="report.html", type="html", size=25000)
            }
        """
        pass
```

**Config ABC Structure**:
```python
class Config(ABC):
    """
    Abstract base class for configuration loading/saving.

    Per Architecture Decision 8: Pluggable config storage.

    v1 Implementations: LocalFileConfig (loads JSON/YAML files)
    v2+ Implementations: DatabaseConfig, PromptServerConfig
    """

    def __init__(self, config_path: str):
        """
        Initialize config with path.

        Args:
            config_path: Path to configuration (file, URL, database key, etc.)
        """
        self.config_path = config_path
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def load(self) -> Dict[str, Any]:
        """
        Load configuration from storage.

        Returns:
            Dict containing configuration data

        Raises:
            StorageError: On load failures
        """
        pass

    @abstractmethod
    async def save(self, config_data: Dict[str, Any]) -> None:
        """
        Save configuration to storage.

        Args:
            config_data: Configuration dictionary to persist

        Raises:
            StorageError: On save failures
        """
        pass
```

**Prompt ABC Structure**:
```python
class Prompt(ABC):
    """
    Abstract base class for prompt template loading/saving.

    Per Architecture Decision 8: Pluggable prompt storage.
    Supports versioned prompts (v1, v2, latest).

    v1 Implementations: LocalFilePrompt (loads TOML templates)
    v2+ Implementations: PromptServerPrompt, DatabasePrompt
    """

    def __init__(self, prompt_name: str, prompt_path: str):
        """
        Initialize prompt with name and path.

        Args:
            prompt_name: Prompt identifier (e.g., "assistant", "researcher")
            prompt_path: Path to prompt storage location
        """
        self.prompt_name = prompt_name
        self.prompt_path = prompt_path
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def load(self, version: str = "latest") -> str:
        """
        Load prompt template by version.

        Args:
            version: Version identifier (e.g., "v1", "v2", "latest")

        Returns:
            str: Prompt template content

        Raises:
            StorageError: If version not found or load fails
        """
        pass

    @abstractmethod
    async def save(self, version: str, content: str) -> None:
        """
        Save prompt template with version.

        Args:
            version: Version identifier to save under
            content: Prompt template content

        Raises:
            StorageError: On save failures
        """
        pass
```

**ArtifactRef Model**:
```python
from pydantic import BaseModel, Field, ConfigDict

class ArtifactRef(BaseModel):
    """
    Reference to a run artifact with metadata.

    Used by Run.artifacts property to describe available artifacts.
    """
    model_config = ConfigDict(extra="ignore")

    path: str = Field(..., description="Relative or absolute path to artifact")
    type: str = Field(..., description="Artifact type (json, jsonl, html, log, etc.)")
    size: int = Field(..., description="Size in bytes")
```

### File Structure Requirements

**Location:** All abstractions go in `src/gavel_ai/storage/base.py`
- Follows established pattern from `processors/base.py`, `judges/base.py`, `reporters/base.py`
- Single `base.py` file contains all ABCs for the storage domain

**Exception:** Add StorageError to `src/gavel_ai/core/exceptions.py`
- Follows established exception hierarchy (ConfigError, ProcessorError, JudgeError, ReporterError)
- Must inherit from GavelError
- Include comprehensive docstring with use cases

**Model:** Add ArtifactRef to `src/gavel_ai/core/models.py`
- Follows established pattern with Pydantic BaseModel
- Use `ConfigDict(extra="ignore")` per project standards
- Include Field descriptions

### Testing Requirements

**Test File:** `tests/unit/storage/test_base.py`

**Test Coverage:**
1. **Abstract Method Verification:** Create concrete test implementations to verify all abstract methods raise NotImplementedError
2. **Instantiation Tests:** Test that ABCs cannot be instantiated directly
3. **Interface Tests:** Verify method signatures and return types
4. **Model Tests:** Test ArtifactRef validation and serialization
5. **Tracer Tests:** Verify tracer is initialized in __init__
6. **Type Hint Tests:** Verify all methods have proper type hints

**Example Test Structure:**
```python
class ConcreteTestRun(Run):
    """Concrete implementation for testing."""
    async def save(self) -> str:
        return "test-path"

    @staticmethod
    async def load(run_id: str) -> Run:
        return ConcreteTestRun(run_id, {})

    @property
    def artifacts(self) -> Dict[str, ArtifactRef]:
        return {}

@pytest.mark.asyncio
async def test_run_save():
    """Run.save() returns storage path."""
    run = ConcreteTestRun("test-run-123", {"eval_name": "test"})
    path = await run.save()
    assert path == "test-path"

@pytest.mark.asyncio
async def test_run_load():
    """Run.load() retrieves run by ID."""
    run = await ConcreteTestRun.load("test-run-123")
    assert run.run_id == "test-run-123"

def test_artifact_ref_model():
    """ArtifactRef validates and serializes correctly."""
    ref = ArtifactRef(path="results.jsonl", type="jsonl", size=1024)
    assert ref.path == "results.jsonl"
    assert ref.type == "jsonl"
    assert ref.size == 1024
```

### Previous Story Intelligence

**Story 5.3 (OneShot Reporter - just completed):**
- Pattern established: ABC in `reporters/base.py` with `Reporter` class
- Uses TYPE_CHECKING for circular import avoidance
- References Architecture Decision in docstring
- Tracer initialized in __init__: `self.tracer = get_tracer(__name__)`
- Abstract method with comprehensive docstring including Args, Returns, Raises
- Config passed in constructor

**Key Learnings:**
1. Use TYPE_CHECKING for forward references to avoid circular imports
2. Include Architecture Decision reference in class docstring
3. Initialize tracer in __init__ for OpenTelemetry spans
4. Use comprehensive docstrings with examples where helpful
5. Abstract methods use `pass` (not `...`)

### Git Intelligence Summary

Recent commits show:
1. **b01f044**: Epic 3 & 4 completed - established processor, judge patterns
2. **39c02d1**: Epic 4 documented - judge ABCs in `judges/base.py`
3. All ABCs follow consistent pattern: base.py in domain folder

**Code Patterns Established:**
- ABC imports: `from abc import ABC, abstractmethod`
- Tracer: `from gavel_ai.telemetry import get_tracer`
- Models: `from gavel_ai.core.models import <Model>`
- Exceptions: `from gavel_ai.core.exceptions import <Error>`
- Type hints required on all methods
- Async methods for IO operations

### Latest Tech Information

**Python 3.10+ ABC Best Practices:**
- Use `@abstractmethod` decorator for abstract methods
- Use `@staticmethod` + `@abstractmethod` for static abstract methods
- Use `@property` + `@abstractmethod` for abstract properties
- Type hints required: Use `from typing import Dict, Any` for Python 3.10 compatibility

**Pydantic v2 Best Practices:**
- Use `ConfigDict(extra="ignore")` for forward compatibility
- Use `Field(..., description="...")` for field documentation
- Models auto-validate on instantiation

### Project Context Reference

See [project-context.md](../../planning-artifacts/project-context.md) for:
- Naming conventions (snake_case functions, PascalCase classes)
- Type hint requirements (all method signatures)
- Logging format standards
- Testing standards (70%+ coverage)
- Exception naming patterns (<Concept>Error)

See [architecture.md](../../planning-artifacts/architecture.md) for:
- Decision 8: Storage Abstraction & Extensibility (lines 477-513)
- Project structure (lines 105-151)
- Technology stack (Pydantic-AI, pytest, Black, Ruff, Mypy)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

