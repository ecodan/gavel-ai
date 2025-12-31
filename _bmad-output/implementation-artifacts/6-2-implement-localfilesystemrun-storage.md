# Story 6.2: Implement LocalFilesystemRun Storage

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want runs stored on the filesystem,
So that v1 evaluations are simple, versionable, and human-readable.

## Acceptance Criteria

- **Given** an evaluation completes
  **When** run is saved
  **Then** the run directory is created at: `.gavel/evaluations/<eval-name>/runs/run-<YYYYMMDD-HHMMSS>/`

- **Given** the run directory exists
  **When** artifacts are saved
  **Then** they're stored in the correct locations:
  - manifest.json
  - config/ (copy of all eval configs)
  - telemetry.jsonl
  - results.jsonl
  - run_metadata.json
  - gavel.log
  - report.html

- **Given** a run is completed
  **When** it's examined on disk
  **Then** all files are readable, inspectable, and versionable (git-friendly)

**Related Requirements:** FR-3.1, FR-3.2, FR-8.6, Decision 8

## Tasks / Subtasks

- [ ] Create LocalFilesystemRun class in src/gavel_ai/storage/filesystem.py (AC: 1, 2, 3)
  - [ ] Inherit from Run ABC (Story 6.1)
  - [ ] Implement __init__ with run_id, eval_name, metadata, base_dir
  - [ ] Implement async save() method creating directory structure
  - [ ] Implement static async load(run_id) method
  - [ ] Implement artifacts property returning Dict[str, ArtifactRef]
  - [ ] Add OpenTelemetry spans for save/load operations
  - [ ] Reference Architecture Decision 8 in docstring

- [ ] Implement directory creation logic (AC: 1)
  - [ ] Create .gavel/evaluations/<eval-name>/runs/ structure
  - [ ] Generate run directory: run-<YYYYMMDD-HHMMSS>/
  - [ ] Handle existing directories gracefully
  - [ ] Set appropriate permissions (readable, git-friendly)

- [ ] Implement artifact saving methods (AC: 2)
  - [ ] save_manifest() for manifest.json
  - [ ] save_config() for config/ directory
  - [ ] save_telemetry() for telemetry.jsonl
  - [ ] save_results() for results.jsonl
  - [ ] save_metadata() for run_metadata.json
  - [ ] save_log() for gavel.log
  - [ ] save_report() for report.html
  - [ ] All methods update artifacts property

- [ ] Implement artifact loading methods (AC: 3)
  - [ ] load_manifest() from manifest.json
  - [ ] load_config() from config/ directory
  - [ ] load_telemetry() from telemetry.jsonl
  - [ ] load_results() from results.jsonl
  - [ ] load_metadata() from run_metadata.json
  - [ ] load_log() from gavel.log
  - [ ] load_report() from report.html

- [ ] Update exports in src/gavel_ai/storage/__init__.py (AC: All)
  - [ ] Export LocalFilesystemRun

- [ ] Write comprehensive tests in tests/unit/storage/test_filesystem.py (AC: All)
  - [ ] Test directory creation at correct path
  - [ ] Test all artifact save operations
  - [ ] Test all artifact load operations
  - [ ] Test save() creates complete run directory
  - [ ] Test load() reconstructs run with all artifacts
  - [ ] Test artifacts property returns correct ArtifactRefs
  - [ ] Test error handling (permission errors, missing files)
  - [ ] Use tmp_path fixture for filesystem isolation
  - [ ] Achieve 70%+ coverage

## Dev Notes

### Architecture Context

This story implements **LocalFilesystemRun**, the v1 concrete implementation of Run ABC from Story 6.1.

**Key Architectural Principles (Decision 8):**
- Domain-driven storage: Run knows how to save/load itself
- Human-readable artifacts: JSON/JSONL for git-friendliness
- Isolated run directories: Each run self-contained
- v1 foundation: All Epic 6 stories build on this implementation

**Directory Structure:**
```
.gavel/
└── evaluations/
    └── <eval-name>/
        └── runs/
            └── run-20251230-120000/
                ├── manifest.json
                ├── config/
                │   ├── eval_config.json
                │   ├── agents.json
                │   ├── scenarios.json
                │   └── judges.json
                ├── telemetry.jsonl
                ├── results.jsonl
                ├── run_metadata.json
                ├── gavel.log
                └── report.html
```

### Dependencies on Previous Stories

**CRITICAL: Story 6.1 (Run ABC) must be complete before starting this story.**
- Requires Run ABC interface definition
- Requires ArtifactRef model
- Requires StorageError exception

**From Epic 4 (Judging):**
- Story 4.6 (Result Storage) creates results.jsonl - this story copies it to run directory
- Story 4.5 (Judge Execution) generates telemetry - this story persists telemetry.jsonl

**From Epic 5 (Reporting):**
- Story 5.3 (OneShot Reporter) generates report.html - this story saves it as artifact

### Implementation Patterns

**LocalFilesystemRun Class Structure:**
```python
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from gavel_ai.storage.base import Run
from gavel_ai.core.models import ArtifactRef
from gavel_ai.core.exceptions import StorageError
from gavel_ai.telemetry import get_tracer

class LocalFilesystemRun(Run):
    """
    Filesystem-based Run implementation.

    Per Architecture Decision 8: v1 storage uses local filesystem
    with human-readable artifacts for git-friendliness.

    Directory structure: .gavel/evaluations/<eval-name>/runs/run-<timestamp>/
    """

    def __init__(
        self,
        run_id: str,
        eval_name: str,
        metadata: Dict[str, Any],
        base_dir: str = ".gavel"
    ):
        """
        Initialize filesystem run.

        Args:
            run_id: Unique run identifier (e.g., "run-20251230-120000")
            eval_name: Evaluation name for directory organization
            metadata: Run metadata dict
            base_dir: Base directory for .gavel storage (default: ".gavel")
        """
        super().__init__(run_id, metadata)
        self.eval_name = eval_name
        self.base_dir = Path(base_dir)
        self.run_dir = self.base_dir / "evaluations" / eval_name / "runs" / run_id
        self._artifacts: Dict[str, ArtifactRef] = {}

    async def save(self) -> str:
        """
        Save run to filesystem.

        Creates directory structure and persists all artifacts.

        Returns:
            str: Path to run directory

        Raises:
            StorageError: On directory creation or save failures
        """
        with self.tracer.start_as_current_span("storage.save") as span:
            span.set_attribute("storage.type", "filesystem")
            span.set_attribute("run.id", self.run_id)
            span.set_attribute("run.directory", str(self.run_dir))

            try:
                # Create directory structure
                self.run_dir.mkdir(parents=True, exist_ok=True)
                (self.run_dir / "config").mkdir(exist_ok=True)

                # Save all artifacts (implemented in separate methods)
                await self.save_manifest()
                await self.save_config()
                await self.save_telemetry()
                await self.save_results()
                await self.save_metadata()
                await self.save_log()
                await self.save_report()

                return str(self.run_dir)

            except (OSError, PermissionError) as e:
                raise StorageError(
                    f"StorageError: Failed to save run {self.run_id} - {e}"
                )

    @staticmethod
    async def load(run_id: str, base_dir: str = ".gavel") -> "LocalFilesystemRun":
        """
        Load run from filesystem by ID.

        Args:
            run_id: Run identifier to load
            base_dir: Base directory for .gavel storage

        Returns:
            LocalFilesystemRun: Loaded run instance

        Raises:
            StorageError: If run not found or load fails
        """
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("storage.load") as span:
            span.set_attribute("storage.type", "filesystem")
            span.set_attribute("run.id", run_id)

            # Find run directory by searching evaluations
            base_path = Path(base_dir)
            eval_dirs = base_path.glob("evaluations/*/runs/" + run_id)

            try:
                run_dir = next(eval_dirs)
            except StopIteration:
                raise StorageError(
                    f"StorageError: Run {run_id} not found - Check run ID"
                )

            # Extract eval_name from path
            eval_name = run_dir.parent.parent.name

            # Load metadata first to reconstruct run
            metadata = await cls._load_metadata_file(run_dir)

            # Create run instance
            run = LocalFilesystemRun(run_id, eval_name, metadata, base_dir)

            # Load all artifacts
            await run.load_manifest()
            await run.load_config()
            await run.load_telemetry()
            await run.load_results()
            await run.load_log()
            await run.load_report()

            return run

    @property
    def artifacts(self) -> Dict[str, ArtifactRef]:
        """
        Get dictionary of run artifacts.

        Returns:
            Dict mapping artifact names to ArtifactRef instances
        """
        return self._artifacts

    async def save_manifest(self) -> None:
        """Save manifest.json artifact."""
        manifest_path = self.run_dir / "manifest.json"
        # Write manifest content (from self.metadata or separate manifest data)
        # Update self._artifacts with ArtifactRef
        self._artifacts["manifest"] = ArtifactRef(
            path=str(manifest_path),
            type="json",
            size=manifest_path.stat().st_size
        )

    # Similar methods for save_config, save_telemetry, etc.
```

### File Structure Requirements

**New File:** `src/gavel_ai/storage/filesystem.py`
- Contains LocalFilesystemRun implementation
- Follows pattern from `storage/base.py` (Story 6.1)

**Directory Creation:**
- Use `pathlib.Path` for cross-platform compatibility
- Use `mkdir(parents=True, exist_ok=True)` for safe directory creation
- Handle permission errors with StorageError

**File Writing:**
- Use async file I/O for consistency (aiofiles or pathlib.Path.write_text)
- JSON files: Use json.dumps with indent=2 for readability
- JSONL files: One JSON object per line
- Text files: UTF-8 encoding

### Testing Requirements

**Test File:** `tests/unit/storage/test_filesystem.py`

**Test Strategy:**
1. Use `tmp_path` fixture for isolated filesystem operations
2. Mock file I/O errors to test error handling
3. Verify directory structure matches specification
4. Test round-trip: save() then load() produces identical run

**Example Tests:**
```python
@pytest.mark.asyncio
async def test_save_creates_directory_structure(tmp_path):
    """LocalFilesystemRun.save() creates correct directory structure."""
    run = LocalFilesystemRun(
        run_id="run-20251230-120000",
        eval_name="test-eval",
        metadata={"eval_name": "test-eval"},
        base_dir=str(tmp_path)
    )

    path = await run.save()

    expected_dir = tmp_path / "evaluations/test-eval/runs/run-20251230-120000"
    assert expected_dir.exists()
    assert expected_dir.is_dir()
    assert (expected_dir / "config").exists()

@pytest.mark.asyncio
async def test_load_reconstructs_run(tmp_path):
    """LocalFilesystemRun.load() reconstructs saved run."""
    # Save a run
    original = LocalFilesystemRun(
        "run-test", "eval-test", {"key": "value"}, str(tmp_path)
    )
    await original.save()

    # Load it back
    loaded = await LocalFilesystemRun.load("run-test", str(tmp_path))

    assert loaded.run_id == original.run_id
    assert loaded.eval_name == original.eval_name
    assert loaded.metadata == original.metadata
```

### Previous Story Intelligence

**Story 6.1 (Run ABC - just completed):**
- Defined Run ABC interface with save(), load(), artifacts
- Defined ArtifactRef model for artifact metadata
- Established StorageError exception

**Key Learnings:**
1. Use async methods for I/O operations (save/load)
2. Tracer spans emit storage.type, run.id, run.directory attributes
3. Static load() method reconstructs run from storage
4. artifacts property returns Dict[str, ArtifactRef]

### References

- [Source: architecture.md#Decision 8: Storage Abstraction] (lines 477-513)
- [Source: epics.md#Story 6.2] (lines 1232-1259)
- [Source: project-context.md#File System & Transparency] (section on human-readable artifacts)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

