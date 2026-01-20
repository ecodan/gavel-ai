# Story C-7.2: Implement `gavel conversational run` Execution

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want `gavel conversational run --eval <name>` to execute conversations end-to-end,
so that I can test dialogue systems comprehensively.

## Acceptance Criteria

1. **Given** `gavel conversational run --eval my_conv_eval` executed
   **When** runs
   **Then** orchestrates: ValidateStep → GenerateStep (optional) → ConversationalProcessingStep → JudgeRunnerStep → ReportingStep

2. **Given** execution progresses
   **When** running
   **Then** progress indicators shown: "Executing scenario 3/10 with variant Claude..."

3. **Given** run completes successfully
   **When** finished
   **Then** run directory created: `runs/<timestamp>/` with all artifacts

4. **Given** invalid config detected
   **When** execution attempted
   **Then** ConfigError raised with clear recovery guidance before execution starts

5. **Given** partial failure during execution (one scenario fails)
   **When** error_handling="collect_all"
   **Then** other scenarios continue; failed scenario recorded; run completes with partial results

## Tasks / Subtasks

- [ ] Task 1: Create `conv run` CLI command (AC: 1)
  - [ ] Subtask 1.1: Add `run` subcommand to `conv` command group in Typer
  - [ ] Subtask 1.2: Add `--eval` parameter for evaluation name
  - [ ] Subtask 1.3: Add optional `--filter-scenarios`, `--filter-variants` parameters for selective execution
  - [ ] Subtask 1.4: Add optional `--generate` flag to trigger GenerateStep before processing
- [ ] Task 2: Implement workflow orchestration (AC: 1)
  - [ ] Subtask 2.1: Wire CLI command to conversational workflow orchestration
  - [ ] Subtask 2.2: Chain steps: ValidateStep → GenerateStep (if --generate) → ConversationalProcessingStep
  - [ ] Subtask 2.3: Chain JudgeRunnerStep after processing
  - [ ] Subtask 2.4: Chain ReportingStep at end of workflow
- [ ] Task 3: Implement pre-execution validation (AC: 4)
  - [ ] Subtask 3.1: Validate eval_config.json schema
  - [ ] Subtask 3.2: Validate scenarios.json against ConversationScenario schema
  - [ ] Subtask 3.3: Validate agents.json and model availability
  - [ ] Subtask 3.4: Raise ConfigError with recovery guidance if validation fails
- [ ] Task 4: Create run directory with timestamped isolation (AC: 3)
  - [ ] Subtask 4.1: Generate timestamp for run (format: YYYYMMDD-HHMMSS)
  - [ ] Subtask 4.2: Create runs/<timestamp>/ directory
  - [ ] Subtask 4.3: Copy eval configs to run directory for reproducibility
- [ ] Task 5: Implement progress reporting (AC: 2)
  - [ ] Subtask 5.1: Display progress for each scenario: "Executing scenario N/M..."
  - [ ] Subtask 5.2: Display variant info: "...with variant <agent_name>"
  - [ ] Subtask 5.3: Display turn count for multi-turn conversations as they progress
- [ ] Task 6: Execute ConversationalProcessingStep (AC: 1, 2, 3)
  - [ ] Subtask 6.1: Instantiate ConversationalProcessingStep with loaded config
  - [ ] Subtask 6.2: Execute step with loaded scenarios and agents
  - [ ] Subtask 6.3: Capture results_raw.jsonl output
- [ ] Task 7: Implement error handling and partial failure (AC: 5)
  - [ ] Subtask 7.1: Implement error_handling="collect_all" mode
  - [ ] Subtask 7.2: Catch individual scenario errors and record in results
  - [ ] Subtask 7.3: Continue execution after scenario failure
  - [ ] Subtask 7.4: Record failed scenarios in manifest
- [ ] Task 8: Wire judging and reporting steps (AC: 1, 3)
  - [ ] Subtask 8.1: Execute JudgeRunnerStep after processing
  - [ ] Subtask 8.2: Execute ReportingStep after judging
  - [ ] Subtask 8.3: Ensure all artifacts written to run directory

## Dev Notes

- This is the primary entry point for conversational evaluation execution
- Follow workflow orchestration patterns from Epic 3 (OneShot execution)
- ConversationalProcessingStep is implemented in Epic C-3
- JudgeRunnerStep is enhanced for conversational in Epic C-4
- ReportingStep includes conversational templates from Epic C-6
- Progress display should use same logging/formatting as OneShot workflow

### Architecture Alignment

- **Orchestration Pattern**: Use `gavel_ai.workflows.conversational_workflow.ConversationalWorkflow`
- **CLI Integration**: Extend `src/gavel_ai/cli/commands/conv.py` with `run` subcommand
- **Run Context**: Use `LocalRunContext` to manage run directory and artifacts
- **Config Loading**: Load from `.gavel/evaluations/<name>/config/`
- **Error Handling**: Use project's error categories (ConfigError, ExecutionError, etc.)

### Project Structure Notes

- CLI code: `src/gavel_ai/cli/commands/conv.py`
- Workflow: `src/gavel_ai/workflows/conversational_workflow.py` (may exist from earlier stories)
- Steps used: ConversationalProcessingStep, JudgeRunnerStep, ReportingStep, ValidateStep
- Run storage: `.gavel/evaluations/<name>/runs/<timestamp>/`

### References

- [Source: epics-conversational-eval.md#Story-C7.2](epics-conversational-eval.md#Story-C7.2)
- [Source: _bmad-output/implementation-artifacts/c-3-2-implement-conversationalprocessingstep.md](c-3-2-implement-conversationalprocessingstep.md)
- [Source: _bmad-output/implementation-artifacts/c-4-4-enhance-judgerrunnerstep-for-multi-level-orchestration.md](c-4-4-enhance-judgerrunnerstep-for-multi-level-orchestration.md)
- [Source: architecture.md#Workflow-Execution](../../planning-artifacts/architecture.md#Workflow-Execution)
- [Source: architecture.md#Error-Handling](../../planning-artifacts/architecture.md#Error-Handling)
- Related Requirements: FR-C7.2, FR-2.1 (execution), FR-2.5 (selective runs), FR-3.1 (run isolation)

## Dev Agent Record

### Agent Model Used

Claude-4.5-Sonnet-latest

### Debug Log References

### Completion Notes List

### File List
