# Story 6.4: Implement Run History Tracking

Status: ready-for-dev

## Story

As a user,
I want to list all completed runs with summaries,
So that I can track evaluation history and compare variants over time.

## Acceptance Criteria

**NOTE: CLI commands deferred to Epic 7. Epic 6 provides API foundation only.**

- **Given** multiple runs have completed
  **When** `await RunHistory().list_runs()` is called
  **Then** all runs are returned with: timestamp, eval name, variant count, status ✅ IMPLEMENTED

- **Given** filtering by evaluation is needed
  **When** `await RunHistory().list_runs(eval_name="test")` is called
  **Then** only runs for that evaluation are shown ✅ IMPLEMENTED

- **Given** runs exist from different dates
  **When** `await RunHistory().list_runs(after=datetime(...))` is called
  **Then** only runs after that date are shown ✅ IMPLEMENTED

- **Given** run history is large
  **When** `list_runs(limit=100, offset=0)` is called
  **Then** pagination is supported ✅ IMPLEMENTED

- **DEFERRED** `gavel oneshot list` CLI command → Epic 7 (OneShot CLI Implementation)
- **DEFERRED** Rich table output formatting → Epic 7

**Related Requirements:** FR-3.4, FR-7.6

## Tasks / Subtasks

- [ ] Create RunHistory class in src/gavel_ai/storage/history.py (AC: 1, 2, 3, 4)
  - [ ] list_runs() method with filters
  - [ ] Filter by eval_name
  - [ ] Filter by date range (after, before)
  - [ ] Return run summaries (timestamp, eval_name, variant_count, best_variant)
  - [ ] Add pagination support

- [ ] Add CLI command in src/gavel_ai/cli/workflows/oneshot.py (AC: 1, 2, 3, 4)
  - [ ] `gavel oneshot list` command
  - [ ] --eval filter option
  - [ ] --after date filter option
  - [ ] --before date filter option
  - [ ] Rich table output formatting

- [ ] Write comprehensive tests (AC: All)
  - [ ] tests/unit/storage/test_history.py for RunHistory
  - [ ] tests/unit/cli/test_oneshot_list.py for CLI command
  - [ ] Test filtering by eval_name
  - [ ] Test filtering by date range
  - [ ] Test pagination
  - [ ] Achieve 70%+ coverage

## Dev Notes

### Architecture Context

This story implements **Run History Tracking** enabling users to list and filter completed runs.

**Key Features:**
- List all runs across all evaluations
- Filter by evaluation name
- Filter by date range
- Pagination for large histories
- Rich CLI table output

### Dependencies

**CRITICAL: Stories 6.1-6.3 must be complete (Run ABC, LocalFilesystemRun, Manifest).**

### Implementation Patterns

```python
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from gavel_ai.storage.base import Run

class RunHistory:
    """Track and query run history."""

    def __init__(self, base_dir: str = ".gavel"):
        self.base_dir = Path(base_dir)

    async def list_runs(
        self,
        eval_name: Optional[str] = None,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List runs with optional filters.

        Returns list of run summaries with pagination.
        """
        # Scan .gavel/evaluations/*/runs/* for all runs
        # Load manifests
        # Filter by criteria
        # Return summaries
        pass
```

### References

- [Source: epics.md#Story 6.4] (lines 1291-1315)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

