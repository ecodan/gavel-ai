# Story 6.7: Implement Run Archive & Export

Status: ready-for-dev

## Story

As a user,
I want to export runs for long-term storage or sharing,
So that important evaluations can be preserved and reproduced.

## Acceptance Criteria

**NOTE: CLI commands deferred to Epic 7. Epic 6 provides API foundation only.**

- **Given** a completed run exists
  **When** `await RunArchiver().export_run(run_id, "run.zip")` is called
  **Then** the entire run (configs, scenarios, results, artifacts) is exported as ZIP ✅ IMPLEMENTED

- **Given** a ZIP file from another machine exists
  **When** `await RunArchiver().import_run("run.zip")` is called
  **Then** the run is re-imported with all artifacts intact ✅ IMPLEMENTED

- **Given** imported run exists
  **When** examined via `LocalFilesystemRun.load()`
  **Then** it can be used for re-judging, re-reporting, or analysis ✅ IMPLEMENTED

- **DEFERRED** `gavel export` CLI command → Epic 7 (OneShot CLI Implementation)
- **DEFERRED** `gavel import` CLI command → Epic 7
- **DEFERRED** Progress indicators for large exports → Epic 7

**Related Requirements:** FR-3.5

## Tasks / Subtasks

- [ ] Create RunArchiver class in src/gavel_ai/storage/archive.py (AC: 1, 2)
  - [ ] export_run(run_id: str, output_path: str) method
  - [ ] import_run(zip_path: str) method
  - [ ] Use zipfile for compression
  - [ ] Preserve directory structure in zip

- [ ] Add CLI commands in src/gavel_ai/cli/main.py (AC: 1, 2)
  - [ ] `gavel export` command with --run and --format options
  - [ ] `gavel import` command with --file option
  - [ ] Progress indicators for large exports
  - [ ] Success confirmation with file size

- [ ] Write comprehensive tests (AC: All)
  - [ ] tests/unit/storage/test_archive.py
  - [ ] Test export creates valid zip
  - [ ] Test import reconstructs run
  - [ ] Test round-trip (export → import → verify)
  - [ ] Achieve 70%+ coverage

## Dev Notes

### Architecture Context

This story implements **Run Archive & Export** for portability and sharing.

**Archive Format:**
- ZIP file containing complete run directory
- Preserves directory structure
- Includes all artifacts (configs, results, reports)

### Dependencies

**CRITICAL: Stories 6.1-6.2 must be complete (Run ABC, LocalFilesystemRun).**

### Implementation Patterns

```python
import zipfile
from pathlib import Path

class RunArchiver:
    """Export and import runs as zip archives."""

    async def export_run(self, run_id: str, output_path: str) -> str:
        """Export run to zip file."""
        run = await LocalFilesystemRun.load(run_id)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for artifact in run.artifacts.values():
                zf.write(artifact.path)

        return output_path

    async def import_run(self, zip_path: str) -> str:
        """Import run from zip file."""
        # Extract to temporary location
        # Move to .gavel/evaluations/
        # Return run_id
        pass
```

### References

- [Source: epics.md#Story 6.7] (lines 1371-1391)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

