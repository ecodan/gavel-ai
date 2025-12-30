# Story 3.7: Implement Timeout & Retry Logic

Status: done

## Story

As a developer,
I want formalized retry logic with exponential backoff,
So that transient failures are handled consistently across all processors.

## Acceptance Criteria

1. **RetryConfig:**
   - Given RetryConfig is defined
   - When configured
   - Then max_retries, delays, backoff_factor, jitter are customizable

2. **Exponential Backoff:**
   - Given retry attempts occur
   - When delays are calculated
   - Then delays increase exponentially with jitter

3. **Transient Error Handling:**
   - Given retry_with_backoff() is called
   - When transient exceptions occur
   - Then retries happen with backoff delays

4. **Non-Transient Error Handling:**
   - Given non-transient errors occur
   - When retry_with_backoff() executes
   - Then errors fail immediately without retry

## Tasks / Subtasks

- [x] Task 1: Create retry module
  - [x] Create src/gavel_ai/core/retry.py
  - [x] Define RetryConfig class
  - [x] Define retry_with_backoff() async function

- [x] Task 2: Implement RetryConfig
  - [x] Add max_retries, initial_delay, max_delay parameters
  - [x] Add backoff_factor for exponential scaling
  - [x] Add jitter toggle for randomness
  - [x] Implement calculate_delay() with jitter

- [x] Task 3: Implement retry_with_backoff()
  - [x] Accept async callable and retry config
  - [x] Accept transient_exceptions tuple
  - [x] Retry on transient errors with exponential backoff
  - [x] Fail immediately on non-transient errors
  - [x] Wrap final failure as ProcessorError

- [x] Task 4: Write comprehensive tests (8 tests)
  - [x] Test RetryConfig defaults
  - [x] Test exponential backoff calculation
  - [x] Test delay capping at max_delay
  - [x] Test success on first attempt
  - [x] Test success after retries
  - [x] Test max retries exceeded
  - [x] Test non-transient error fails immediately
  - [x] Test ProcessorError propagation

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Completion Notes
- ✅ Created retry module (116 lines)
- ✅ RetryConfig with exponential backoff and jitter
- ✅ retry_with_backoff() for async operations
- ✅ Transient vs non-transient error differentiation
- ✅ 8 comprehensive unit tests (all passing)
- ✅ Architecture Decision 7 compliance (exponential backoff with jitter)

### File List

**New Files:**
- `src/gavel_ai/core/retry.py` (116 lines)
- `tests/unit/test_retry.py` (8 tests)

## Change Log

- **2025-12-29**: ✅ Implementation complete - 8 tests passing, all ACs satisfied
