---
summary: "Add gavel-ai-level retry on top of DeepEval's internal Tenacity retry for rate-limit errors. Generalize retry_with_backoff() to support custom error classes and transient predicates. When DeepEval exhausts its 2 internal retries on RateLimitError, gavel-ai now retries 3 times with exponential backoff before failing."
phase: "tasks"
when_to_load:
  - "When reviewing the judge rate-limit retry implementation"
depends_on: []
modules:
  - "core/retry.py"
  - "judges/deepeval_judge.py"
  - "pyproject.toml"
index:
  implementation: "## Implementation"
next_section: null
---

# Tweaklet: judge-rate-limit-retry

## Problem

When DeepEval evaluates scenarios and hits a provider rate-limit error, DeepEval's internal Tenacity decorator retries up to 2 times. When those are exhausted, Tenacity raises `tenacity.RetryError`. Gavel-ai was catching this as a bare exception and wrapping it as `JudgeError`, then `fail_fast` mode in `JudgeExecutor` terminated the entire batch immediately.

**Impact**: Any eval run hitting rate limits would fail completely instead of waiting and retrying.

## Tasks

- [x] Generalize `retry_with_backoff()` in `core/retry.py` to support:
  - `error_class` parameter (defaults to `ProcessorError`, can be `JudgeError` for judges)
  - `transient_predicate` callable to inspect exceptions and decide if they're transient
  - Simplified non-transient handling (bare `raise` instead of wrapping)
- [x] Add rate-limit retry to `DeepEvalJudge.evaluate()`:
  - Helper `_is_rate_limit_retry_error()` detects rate-limit cause in `tenacity.RetryError`
  - Wrap metric evaluation with `retry_with_backoff()` configured for 3 retries, 5s–60s backoff with jitter
  - Log warnings per retry attempt
- [x] Add `tenacity` as explicit direct dependency in `pyproject.toml`
- [x] Update `tests/unit/test_retry.py`: 2 updated + 2 new tests for generalized logic
- [x] Add `tests/unit/test_deepeval_judge.py::TestRateLimitRetry`: 3 tests for rate-limit retry behavior
- [x] Verify: 910 unit tests pass, 83% coverage (gate: 70%)

## Implementation

**Files changed**:
- `src/gavel_ai/core/retry.py` — Generalized retry function
- `src/gavel_ai/judges/deepeval_judge.py` — Rate-limit retry in evaluate()
- `tests/unit/test_retry.py` — Updated + new tests for generalized logic
- `tests/unit/test_deepeval_judge.py` — New `TestRateLimitRetry` class
- `pyproject.toml` — Added `tenacity` dependency

**Commit**: `d60682b feat: Add rate-limit retry logic for DeepEval judge evaluations`

## Success Criteria

- [x] DeepEval rate-limit errors are retried at gavel-ai level
- [x] Auth errors (non-rate-limit) fail immediately without retry
- [x] Exponential backoff with jitter for future parallel evals
- [x] All unit tests pass at ≥70% coverage
- [x] No regressions in existing test suite
