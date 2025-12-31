# Story 6.5: Implement Milestone Marking

Status: ready-for-dev

## Story

As a user,
I want to mark important runs as milestones,
So that baseline and production-ready evaluations are preserved and easy to find.

## Acceptance Criteria

**NOTE: CLI commands deferred to Epic 7. Epic 6 provides API foundation only.**

- **Given** a completed run is loaded via API
  **When** `await run.mark_milestone("Baseline for v1.0")` is called
  **Then** the run is marked as a milestone ✅ IMPLEMENTED

- **Given** the manifest.json is examined
  **When** the milestone flag is checked
  **Then** it's set to true with the comment and timestamp ✅ IMPLEMENTED

- **Given** milestone runs are excluded from cleanup
  **When** RunCleaner.cleanup_runs() is called
  **Then** milestone runs are preserved (non-milestone old runs are deleted) ✅ IMPLEMENTED

- **DEFERRED** `gavel oneshot milestone` CLI command → Epic 7 (OneShot CLI Implementation)
- **DEFERRED** `gavel oneshot list --milestones` CLI filtering → Epic 7

**Related Requirements:** FR-3.7

## Tasks / Subtasks

- [ ] Update Manifest model in src/gavel_ai/core/models.py (AC: 2)
  - [ ] Add is_milestone: bool field
  - [ ] Add milestone_comment: Optional[str] field
  - [ ] Add milestone_timestamp: Optional[datetime] field

- [ ] Add mark_milestone() to LocalFilesystemRun (AC: 1, 2)
  - [ ] Update manifest with milestone fields
  - [ ] Save updated manifest.json

- [ ] Add CLI command in src/gavel_ai/cli/workflows/oneshot.py (AC: 1, 4)
  - [ ] `gavel oneshot milestone` command
  - [ ] --run option for run_id
  - [ ] --comment option for milestone comment
  - [ ] Success confirmation output

- [ ] Update list command for milestone filtering (AC: 4)
  - [ ] Add --milestones flag
  - [ ] Display milestone indicator and comment

- [ ] Update RunHistory filtering (AC: 4)
  - [ ] Filter for is_milestone=True

- [ ] Write comprehensive tests (AC: All)
  - [ ] Test mark_milestone() updates manifest
  - [ ] Test CLI milestone command
  - [ ] Test milestone filtering in list
  - [ ] Achieve 70%+ coverage

## Dev Notes

### Architecture Context

This story implements **Milestone Marking** to preserve important runs from cleanup.

**Milestone Fields in Manifest:**
```json
{
  "is_milestone": true,
  "milestone_comment": "Baseline for v1.0",
  "milestone_timestamp": "2025-12-30T14:00:00Z",
  ...
}
```

### Dependencies

**CRITICAL: Stories 6.1-6.4 must be complete.**
- Story 6.3 (Manifest) - extends Manifest model
- Story 6.4 (Run History) - adds milestone filtering

### References

- [Source: epics.md#Story 6.5] (lines 1319-1343)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

