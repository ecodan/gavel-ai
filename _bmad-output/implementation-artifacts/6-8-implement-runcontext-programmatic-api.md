# Story 6.8: Implement RunContext Programmatic API

Status: ready-for-dev

## Story

As a developer,
I want to access run artifacts programmatically (future SDK),
So that custom analysis scripts and notebooks can load and analyze results.

## Acceptance Criteria

- **Given** RunContext API exists
  **When** `run = await Run.load(run_id)` is called
  **Then** the run object is loaded with all artifacts

- **Given** the run object is loaded
  **When** artifacts are accessed
  **Then** they can be read programmatically (results, telemetry, metadata)

- **Given** a developer wants to analyze results
  **When** they use RunContext in a script/notebook
  **Then** all run data is accessible via Python API

**Related Requirements:** FR-6.4

## Tasks / Subtasks

- [ ] Create RunContext wrapper in src/gavel_ai/storage/run_context.py (AC: 1, 2, 3)
  - [ ] load_run(run_id: str) async function
  - [ ] get_results() method returning parsed results
  - [ ] get_telemetry() method returning parsed telemetry
  - [ ] get_metadata() method returning manifest
  - [ ] get_config() method returning eval configs
  - [ ] Convenience methods for common queries

- [ ] Add example usage documentation (AC: 3)
  - [ ] Create examples/analyze_run.py script
  - [ ] Document in README.md
  - [ ] Show notebook usage example

- [ ] Write comprehensive tests (AC: All)
  - [ ] tests/unit/storage/test_run_context.py
  - [ ] Test load_run() loads all artifacts
  - [ ] Test artifact accessor methods
  - [ ] Test with real run data
  - [ ] Achieve 70%+ coverage

## Dev Notes

### Architecture Context

This story implements **RunContext Programmatic API** enabling SDK-style programmatic access to runs.

**Example Usage:**
```python
from gavel_ai.storage import load_run

# Load run
run = await load_run("run-20251230-120000")

# Access artifacts
results = await run.get_results()
telemetry = await run.get_telemetry()
metadata = await run.get_metadata()

# Analyze
for result in results:
    print(f"Variant: {result['variant_id']}, Score: {result['score']}")
```

### Dependencies

**CRITICAL: Stories 6.1-6.3 must be complete (Run ABC, LocalFilesystemRun, Manifest).**

### Implementation Patterns

```python
from typing import List, Dict, Any
from gavel_ai.storage.filesystem import LocalFilesystemRun

async def load_run(run_id: str, base_dir: str = ".gavel") -> LocalFilesystemRun:
    """
    Load run for programmatic access.

    Convenience function for SDK-style usage.
    """
    return await LocalFilesystemRun.load(run_id, base_dir)

class RunContext:
    """High-level API for run artifact access."""

    def __init__(self, run: LocalFilesystemRun):
        self.run = run

    async def get_results(self) -> List[Dict[str, Any]]:
        """Get parsed results from results.jsonl."""
        # Load and parse results.jsonl
        pass

    async def get_telemetry(self) -> List[Dict[str, Any]]:
        """Get parsed telemetry from telemetry.jsonl."""
        # Load and parse telemetry.jsonl
        pass
```

### References

- [Source: epics.md#Story 6.8] (lines 1395-1407)
- [Source: architecture.md#FR-6.4]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

