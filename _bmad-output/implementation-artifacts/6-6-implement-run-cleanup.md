# Story 6.6: Implement Run Cleanup

Status: ready-for-dev

## Story

As a user,
I want old runs cleaned up automatically,
So that disk space is managed and only relevant runs are kept.

## Acceptance Criteria

**NOTE: CLI commands deferred to Epic 7. Epic 6 provides API foundation only.**

- **Given** multiple runs exist, some older than 30 days
  **When** `await RunCleaner().cleanup_runs(older_than="30d")` is called
  **Then** runs older than 30 days are deleted (except milestones) ✅ IMPLEMENTED

- **Given** time expression parsing is needed
  **When** `parse_time_expression("30d")` is called
  **Then** it returns 30 (days) and supports "7d", "1w", "2m", "1y" formats ✅ IMPLEMENTED

- **Given** dry_run mode is enabled
  **When** `cleanup_runs(older_than="30d", dry_run=True)` is called
  **Then** runs that WOULD be deleted are returned (but not actually deleted) ✅ IMPLEMENTED

- **DEFERRED** `gavel clean` CLI command → Epic 7 (OneShot CLI Implementation)
- **DEFERRED** Interactive confirmation prompts → Epic 7

**Related Requirements:** FR-8.7

## Tasks / Subtasks

- [ ] Create RunCleaner class in src/gavel_ai/storage/cleanup.py (AC: 1, 2, 3)
  - [ ] clean_old_runs(older_than: str) method
  - [ ] delete_run(run_id: str) method
  - [ ] find_runs_to_delete() method
  - [ ] Exclude milestone runs from deletion
  - [ ] Parse time expressions (30d, 7d, etc.)

- [ ] Add CLI command in src/gavel_ai/cli/main.py (AC: 1, 2, 3)
  - [ ] `gavel clean` command
  - [ ] --older-than option (e.g., "30d")
  - [ ] --run option for specific run_id
  - [ ] --dry-run flag to preview deletions
  - [ ] Interactive confirmation prompt

- [ ] Write comprehensive tests (AC: All)
  - [ ] tests/unit/storage/test_cleanup.py
  - [ ] Test older-than filtering
  - [ ] Test milestone exclusion
  - [ ] Test specific run deletion
  - [ ] Test time expression parsing
  - [ ] Achieve 70%+ coverage

## Dev Notes

### Architecture Context

This story implements **Run Cleanup** for disk space management.

**Key Principles:**
- NEVER delete milestone runs
- Always confirm before deletion
- Support dry-run mode
- Parse time expressions (30d, 7d, 1y)

### Dependencies

**CRITICAL: Stories 6.1-6.5 must be complete.**
- Story 6.5 (Milestones) - exclude milestone runs

### Implementation Patterns

```python
from datetime import datetime, timedelta
import shutil

class RunCleaner:
    """Clean up old runs from storage."""

    def parse_time_expression(self, expr: str) -> timedelta:
        """Parse 30d, 7d, 1y into timedelta."""
        # Implementation
        pass

    async def clean_old_runs(
        self,
        older_than: str,
        dry_run: bool = False
    ) -> List[str]:
        """Delete runs older than specified time."""
        # Find runs older than threshold
        # Exclude milestones
        # Delete if not dry_run
        pass
```

### References

- [Source: epics.md#Story 6.6] (lines 1347-1367)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

