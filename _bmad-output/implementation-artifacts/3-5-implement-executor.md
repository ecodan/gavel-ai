# Story 3.5: Implement Executor

Status: done

## Story

As a user,
I want concurrent execution of scenarios with configurable error handling,
So that I can efficiently evaluate large batches of inputs.

## Acceptance Criteria

1. **Concurrent Execution:**
   - Given Executor is initialized with parallelism setting
   - When execute() is called with multiple inputs
   - Then inputs are processed in concurrent batches

2. **Error Handling Modes:**
   - Given error_handling is set to "fail_fast" or "collect_all"
   - When errors occur during execution
   - Then behavior matches configured mode

3. **Result Collection:**
   - Given all inputs have been processed
   - When execution completes
   - Then a list of ProcessorResult instances is returned

## Tasks / Subtasks

- [x] Task 1: Create Executor class
  - [x] Accept processor, parallelism, error_handling in constructor
  - [x] Set up tracer for telemetry
  - [x] Validate configuration parameters

- [x] Task 2: Implement concurrent execution
  - [x] Batch inputs based on parallelism
  - [x] Create async tasks for each batch
  - [x] Use asyncio.gather for concurrency

- [x] Task 3: Implement error handling modes
  - [x] fail_fast: Raise on first error
  - [x] collect_all: Wrap errors in ProcessorResult
  - [x] Return all results regardless of errors

- [x] Task 4: Add telemetry
  - [x] Emit executor.run span
  - [x] Add parallelism and error_handling attributes

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Completion Notes
- ✅ Created Executor (86 lines)
- ✅ Concurrent batch processing with asyncio.gather
- ✅ fail_fast and collect_all error handling modes
- ✅ Telemetry spans with executor attributes
- ✅ All ACs satisfied

### File List

**New Files:**
- `src/gavel_ai/core/executor.py` (86 lines)

## Change Log

- **2025-12-29**: ✅ Implementation complete - All ACs satisfied
