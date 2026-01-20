# Story C-7.3: Implement `gavel conversational judge` Re-judging

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want `gavel conversational judge --eval <name> --run <timestamp>` to re-judge,
so that I can iterate on judge definitions without re-running conversations.

## Acceptance Criteria

1. **Given** previous run exists with results_raw.jsonl
   **When** `gavel conversational judge --eval my_conv_eval --run 20260118-100000` executed
   **Then** JudgeRunnerStep loads conversations and applies current judges from eval_config.json

2. **Given** re-judge execution starts
   **When** running
   **Then** progress shown: "Judging conversation N/M..."

3. **Given** re-judge completes
   **When** finished
   **Then** results_judged.jsonl overwritten; manifest.json updated with judge history

4. **Given** report already exists
   **When** re-judge completes
   **Then** old report.html preserved; new report can be generated

## Tasks / Subtasks

- [ ] Task 1: Create `conv judge` CLI command (AC: 1)
  - [ ] Subtask 1.1: Add `judge` subcommand to `conv` command group in Typer
  - [ ] Subtask 1.2: Add `--eval` parameter for evaluation name
  - [ ] Subtask 1.3: Add `--run` parameter for run timestamp
  - [ ] Subtask 1.4: Add optional `--filter-judges` parameter for selective judge execution
- [ ] Task 2: Implement run directory and artifact loading (AC: 1)
  - [ ] Subtask 2.1: Validate eval and run directory structure
  - [ ] Subtask 2.2: Load results_raw.jsonl from run directory
  - [ ] Subtask 2.3: Load current eval_config.json from evaluation directory
  - [ ] Subtask 2.4: Extract conversation transcripts from results_raw
- [ ] Task 3: Implement JudgeRunnerStep execution (AC: 1)
  - [ ] Subtask 3.1: Instantiate JudgeRunnerStep with loaded judges from eval_config.json
  - [ ] Subtask 3.2: Apply judges to each conversation transcript
  - [ ] Subtask 3.3: Generate results_judged.jsonl with judge scores and reasoning
- [ ] Task 4: Implement progress reporting (AC: 2)
  - [ ] Subtask 4.1: Display progress: "Judging conversation N/M..."
  - [ ] Subtask 4.2: Show judge name as they're applied
  - [ ] Subtask 4.3: Display completion percentage
- [ ] Task 5: Implement manifest and artifact management (AC: 3)
  - [ ] Subtask 5.1: Update manifest.json with re-judge execution timestamp
  - [ ] Subtask 5.2: Record judge history showing multiple judge iterations
  - [ ] Subtask 5.3: Overwrite results_judged.jsonl with new scores
  - [ ] Subtask 5.4: Preserve original results_raw.jsonl
- [ ] Task 6: Implement report preservation (AC: 4)
  - [ ] Subtask 6.1: Archive existing report.html with timestamp suffix
  - [ ] Subtask 6.2: Do not auto-regenerate report (user must run `conv report` separately)
  - [ ] Subtask 6.3: Preserve both old and new reports
- [ ] Task 7: Implement error handling (AC: 1)
  - [ ] Subtask 7.1: Validate run exists in runs/<timestamp>/ directory
  - [ ] Subtask 7.2: Validate results_raw.jsonl format
  - [ ] Subtask 7.3: Handle missing or corrupted run artifacts gracefully
  - [ ] Subtask 7.4: Provide clear error messages with recovery guidance

## Dev Notes

- Re-judge is a performance optimization - avoid full execution
- Must load conversation transcripts from results_raw.jsonl (not re-execute)
- Judge definitions come from current eval_config.json (supports iteration on judges)
- Progress display should mirror `conv run` progress format
- Manifest management is critical for audit trail and reproducibility
- Report archival prevents data loss but doesn't auto-regenerate (user must run separately)

### Architecture Alignment

- **CLI Integration**: Extend `src/gavel_ai/cli/commands/conv.py` with `judge` subcommand
- **Run Loading**: Use `LocalRunContext.load_run()` to access existing run
- **Judge Execution**: Use `JudgeRunnerStep` (enhanced in C-4 for conversation-level judges)
- **Artifact Management**: Use `LocalFilesystemRun` storage API
- **Error Handling**: Use project's error categories (RunNotFoundError, ArtifactFormatError, etc.)

### Project Structure Notes

- CLI code: `src/gavel_ai/cli/commands/conv.py`
- Run loading: `gavel_ai.storage.local_run.LocalRunContext`
- Artifacts: `.gavel/evaluations/<name>/runs/<timestamp>/results_raw.jsonl`, `results_judged.jsonl`, `manifest.json`
- Report archival: `.gavel/evaluations/<name>/runs/<timestamp>/report_<timestamp>.html`

### References

- [Source: epics-conversational-eval.md#Story-C7.3](epics-conversational-eval.md#Story-C7.3)
- [Source: _bmad-output/implementation-artifacts/c-4-4-enhance-judgerrunnerstep-for-multi-level-orchestration.md](c-4-4-enhance-judgerrunnerstep-for-multi-level-orchestration.md)
- [Source: _bmad-output/implementation-artifacts/c-5-1-implement-re-judge-cli-command.md](c-5-1-implement-re-judge-cli-command.md)
- [Source: architecture.md#Run-Management](../../planning-artifacts/architecture.md#Run-Management)
- Related Requirements: FR-C7.3, FR-3.3 (re-judging), FR-3.2 (artifact management)

## Dev Agent Record

### Agent Model Used

Claude-4.5-Sonnet-latest

### Debug Log References

### Completion Notes List

### File List
