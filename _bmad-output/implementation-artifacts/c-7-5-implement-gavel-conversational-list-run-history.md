# Story C-7.5: Implement `gavel conversational list` Run History

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want `gavel conversational list --eval <name>` to show run history,
so that I can track evaluation progress.

## Acceptance Criteria

1. **Given** `gavel conversational list` executed
   **When** completed
   **Then** displays all conversational runs with: run_id, timestamp, eval_name, scenario_count, variant_count, status

2. **Given** multiple eval_names exist
   **When** `gavel conversational list --eval specific_eval` filtered
   **Then** only runs for that evaluation shown

3. **Given** runs from different dates
   **When** `gavel conversational list --after 2026-01-15` filtered
   **Then** only runs after that date shown

4. **Given** large run history
   **When** displayed
   **Then** pagination or summary format used for readability

## Tasks / Subtasks

- [ ] Task 1: Create `conv list` CLI command (AC: 1)
  - [ ] Subtask 1.1: Add `list` subcommand to `conv` command group in Typer
  - [ ] Subtask 1.2: Add optional `--eval` parameter for filtering by evaluation name
  - [ ] Subtask 1.3: Add optional `--after` parameter for date filtering (format: YYYY-MM-DD)
- [ ] Task 2: Implement run discovery (AC: 1)
  - [ ] Subtask 2.1: Scan `.gavel/evaluations/` directory for evaluations
  - [ ] Subtask 2.2: For each evaluation, scan `runs/` subdirectory
  - [ ] Subtask 2.3: Load manifest.json from each run to get metadata
  - [ ] Subtask 2.4: Extract run_id, timestamp, scenario_count, variant_count, status
- [ ] Task 3: Implement filtering logic (AC: 2, 3)
  - [ ] Subtask 3.1: Filter by eval_name if `--eval` specified
  - [ ] Subtask 3.2: Filter by date if `--after` specified
  - [ ] Subtask 3.3: Support combining multiple filters
- [ ] Task 4: Implement table display (AC: 1)
  - [ ] Subtask 4.1: Format runs as readable table with columns: run_id, timestamp, eval_name, scenarios, variants, status
  - [ ] Subtask 4.2: Include additional useful columns: judge_count, report_status
  - [ ] Subtask 4.3: Sort by timestamp (newest first)
- [ ] Task 5: Implement pagination (AC: 4)
  - [ ] Subtask 5.1: If >20 runs, display first N with "show more" option
  - [ ] Subtask 5.2: Add `--limit` and `--offset` parameters for pagination
  - [ ] Subtask 5.3: Display summary: "Showing N of M runs"
- [ ] Task 6: Implement run status computation (AC: 1)
  - [ ] Subtask 6.1: Determine if run is complete (has results_judged.jsonl)
  - [ ] Subtask 6.2: Determine if run has report generated
  - [ ] Subtask 6.3: Determine if run is from partial execution or full
  - [ ] Subtask 6.4: Display as "complete", "partial", "judged", "awaiting-report", etc.
- [ ] Task 7: Implement useful output options (AC: 1)
  - [ ] Subtask 7.1: Add `--format json` for programmatic access
  - [ ] Subtask 7.2: Add `--format csv` for spreadsheet import
  - [ ] Subtask 7.3: Add `--verbose` for detailed run information
- [ ] Task 8: Implement error handling and edge cases (AC: 1)
  - [ ] Subtask 8.1: Handle missing or corrupted manifest.json gracefully
  - [ ] Subtask 8.2: Handle empty evaluations directory
  - [ ] Subtask 8.3: Handle invalid date formats in `--after` parameter
  - [ ] Subtask 8.4: Display helpful message if no runs match filters

## Dev Notes

- This is a read-only command that discovers and displays existing runs
- Run history is discovered from filesystem, not a database
- Manifest.json contains all necessary metadata for display
- Status can be computed from artifact presence in run directory
- Large run histories are possible - pagination is important for UX
- The command should be fast - avoid deep scans of run directories
- Output formats (JSON, CSV) enable integration with other tools

### Architecture Alignment

- **CLI Integration**: Extend `src/gavel_ai/cli/commands/conv.py` with `list` subcommand
- **Run Discovery**: Use `gavel_ai.storage.local_run.LocalRunContext.discover_runs()`
- **Manifest Loading**: Load JSON from `runs/<timestamp>/manifest.json`
- **Table Formatting**: Use `rich` library (already used in project) for pretty tables
- **Status Logic**: Compute from artifact presence using helper functions

### Project Structure Notes

- CLI code: `src/gavel_ai/cli/commands/conv.py`
- Run location: `.gavel/evaluations/<name>/runs/<timestamp>/`
- Metadata: `manifest.json` in each run directory
- Discovery helper: `gavel_ai.storage.local_run.LocalRunContext.discover_runs()` method

### References

- [Source: epics-conversational-eval.md#Story-C7.5](epics-conversational-eval.md#Story-C7.5)
- [Source: _bmad-output/implementation-artifacts/6-4-implement-run-history-tracking.md](6-4-implement-run-history-tracking.md)
- [Source: architecture.md#Run-Management](../../planning-artifacts/architecture.md#Run-Management)
- Related Requirements: FR-C7.5, FR-3.4 (run history), FR-7.7 (structured output)

## Dev Agent Record

### Agent Model Used

Claude-4.5-Sonnet-latest

### Debug Log References

### Completion Notes List

### File List
