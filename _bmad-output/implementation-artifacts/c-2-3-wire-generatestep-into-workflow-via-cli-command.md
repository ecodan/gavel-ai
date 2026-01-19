# Story C-2.3: Wire GenerateStep into Workflow via CLI Command

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to use `gavel conv generate --eval <name>` to generate scenarios from a prompt,
so that I can create scenarios without writing JSON manually.

## Acceptance Criteria

1. Given `gavel conv generate --eval my_eval` executed, when runs, then GenerateStep invoked; prompt loaded from prompts/generate_scenarios.toml; scenarios generated and written to data/scenarios.jsonl
2. Given generation completes successfully, when progress displayed, then user sees: "Generated N scenarios with LLM"
3. Given scenarios.jsonl created, when user runs `gavel conv run --eval my_eval`, then existing scenarios.jsonl used (no re-generation unless `gavel conv generate` run again)
4. Given user provides custom prompt with `--prompt-file` flag, when `gavel conv generate --eval my_eval --prompt-file custom_scenarios.toml` executed, then custom prompt used instead of default prompts/generate_scenarios.toml
5. Given generation fails (invalid prompt, LLM error, parsing error), when error caught, then clear error message displayed: "Failed to generate scenarios: [reason]"; scenarios.jsonl not modified/deleted

## Tasks / Subtasks

- [x] Task 1: Add conversational workflow commands to CLI structure (AC: 1)
  - [x] Subtask 1.1: Create `conv` command group in Typer CLI
  - [x] Subtask 1.2: Add `generate` subcommand with `--eval` parameter
  - [x] Subtask 1.3: Add `--prompt-file` optional parameter
- [x] Task 2: Implement generate command workflow (AC: 1, 2, 3)
  - [x] Subtask 2.1: Load evaluation configuration and locate prompt file
  - [x] Subtask 2.2: Instantiate and execute GenerateStep
  - [x] Subtask 2.3: Handle successful generation and progress display
- [x] Task 3: Implement custom prompt support (AC: 4)
  - [x] Subtask 3.1: Validate custom prompt file existence
  - [x] Subtask 3.2: Load custom prompt instead of default
  - [x] Subtask 3.3: Ensure custom prompt follows expected format
- [x] Task 4: Implement error handling and user feedback (AC: 5)
  - [x] Subtask 4.1: Catch LLM generation errors
  - [x] Subtask 4.2: Catch prompt parsing errors
  - [x] Subtask 4.3: Display user-friendly error messages
  - [x] Subtask 4.4: Ensure scenarios.jsonl not left in corrupted state

## Dev Notes

- Extend existing Typer CLI structure with `conv` command group
- Follow established patterns from `oneshot` command implementation
- GenerateStep should be integrated into conversational workflow context
- Error messages should follow project's informative error format (FR-9.1)

### Project Structure Notes

- CLI extension in: src/gavel_ai/cli/workflows/conversational.py
- GenerateStep location: src/gavel_ai/processors/generate_step.py
- Default prompt location: prompts/generate_scenarios.toml
- Output location: data/scenarios.jsonl (consistent with scaffolding)

### References

- [Source: epics-conversational-eval.md#Story-C2.3](epics-conversational-eval.md#Story-C2.3)
- [Source: architecture.md#CLI-Structure](architecture.md#CLI-Structure)
- [Source: architecture.md#Command-Patterns](architecture.md#Command-Patterns)
- [Source: architecture.md#Error-Handling](architecture.md#Error-Handling)
- Related Requirements: FR-C1.2

## Dev Agent Record

### Agent Model Used

Claude-4.5-Sonnet-latest

### Debug Log References

### Completion Notes List

**Implementation Complete (2026-01-18):**
- ✅ **CLI Structure Fix**: Resolved `NameError` by defining Typer `app` in `conv.py`
- ✅ **Command Realignment**: Renamed `run` to `generate` to match Acceptance Criteria
- ✅ **GenerateStep Integration**: Properly wired `generate` command to `GenerateStep` processor using `LocalRunContext`
- ✅ **Test Overhaul**: Replaced fictional tests with real unit tests verifying execution, custom prompts, and error handling
- ✅ **Verification**: Confirmed all 6 unit tests pass and CLI correctly registers `conv` subcommands

**Implementation Status:**
- **Basic CLI Infrastructure**: ✅ Working
- **GenerateStep Integration**: ✅ Complete
- **Scaffolding**: ⏳ Partially implemented (scaffold command exists as placeholder)
- **Full Implementation**: ✅ Complete

**Key Insights:**
- Using `Annotated` in Typer commands ensures Python defaults (like `None`) work correctly in tests without `OptionInfo` interference
- `GenerateStep` integration requires a valid `RunContext`, provided by `LocalRunContext`

### File List

- [src/gavel_ai/cli/commands/conv.py](file:///Users/dan/dev/code/projects/python/gavel-ai/src/gavel_ai/cli/commands/conv.py)
- [tests/unit/cli/commands/test_conv_generate.py](file:///Users/dan/dev/code/projects/python/gavel-ai/tests/unit/cli/commands/test_conv_generate.py)
- [tests/unit/cli/commands/test_conv_generate_simple.py](file:///Users/dan/dev/code/projects/python/gavel-ai/tests/unit/cli/commands/test_conv_generate_simple.py)
