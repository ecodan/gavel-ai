# Logging Architecture Decision

**Project:** gavel-ai
**Date:** 2026-01-03
**Author:** Dev Agent (Amelia) + Dan
**Status:** Complete
**Decision ID:** LOG-ARCH-001
**Story:** Logging Improvements (Chat-driven Enhancement)

---

## Executive Summary

Gavel-ai adopts a **two-tier logging architecture** with environment-controlled verbosity, dual-stream output (console + file), and structured IO event logging. All workflows and features must follow these guidelines to ensure consistent, actionable logging across the system.

**Key Decision:** Separate application-level lifecycle logging from run-level operational logging, with independent log level control and real-time console visibility.

---

## Problem Statement

Before this decision:
- Run-level logging was **file-only** — operators couldn't see progress in real-time
- No mechanism to control log verbosity per layer (app vs run)
- Progress tracking relied on verbose INFO logs that cluttered output
- No structured format for lifecycle events (START/END markers)
- Inconsistent console feedback vs file logs

**Gaps:**
1. Long-running operations (scenario processing, judging) had no real-time visibility
2. Debugging required manual log file inspection
3. Log verbosity was binary (DEBUG mode on/off via `GAVEL_DEBUG`)
4. No standard pattern for major operational phases

---

## Decision: Two-Tier Logging with Console Output

### 1. Logging Architecture

**Tier 1: Application Logger**
- **Output:** `.gavel/gavel.log` (rotating: 10MB, 5 backups) + stdout
- **Scope:** Evaluation creation, startup, shutdown, global errors
- **Level Control:** `LOG_LEVEL_APP` env var (default: `INFO`)
- **Audience:** Operations, high-level monitoring

**Tier 2: Run Logger**
- **Output:** `.gavel/evaluations/{eval}/runs/{run_id}/run.log` + stdout
- **Scope:** Run-specific: config loading, scenario processing, judging, result export
- **Level Control:** `LOG_LEVEL_RUN` env var (default: `INFO`)
- **Audience:** Developers, debugging specific runs

**Console Output**
- Both loggers write to stdout at their configured level
- Structured format: `YYYY-MM-DD HH:MM:SS [LEVEL] <filename:lineno> message`
- File handlers preserve all output; console respects log level
- Example: `2026-01-03 14:30:45 [INFO] <oneshot.py:232> Scenario START: test_subject=claude-sonnet | variant_id=v1`

### 2. Log Level Environment Variables

```bash
# .env configuration
LOG_LEVEL_APP=INFO      # Application logger: DEBUG, INFO (default), WARNING, ERROR, CRITICAL
LOG_LEVEL_RUN=INFO      # Run logger: DEBUG, INFO (default), WARNING, ERROR, CRITICAL
```

**Usage Examples:**
```bash
# Verbose run debugging
LOG_LEVEL_RUN=DEBUG gavel oneshot run --eval my_test

# Only errors to console, full detail in files
LOG_LEVEL_APP=WARNING LOG_LEVEL_RUN=WARNING gavel oneshot run --eval my_test

# Default: INFO level on both
gavel oneshot run --eval my_test
```

### 3. Progress Display with TQDM

For batch operations (scenario processing, judge execution), use TQDM progress bars instead of verbose logging. This prevents log clutter while maintaining real-time visibility.

**Design Principle:** TQDM bar is the primary UI; logging is suppressed during batch operations to keep console clean.

**Implementation Pattern:**
```python
from tqdm import tqdm

# Scenario processing with live description
with tqdm(total=len(inputs), desc="Processing scenarios", unit="scenario") as pbar:
    for batch in batches:
        # ... process batch ...
        pbar.update(len(batch))
        desc = f"Processing scenarios | {latest_scenario_id} | {test_subject} | {variant_id}"
        pbar.set_description(desc)

# Output:
# Processing scenarios | scenario-42 | claude-sonnet | v1 [45/100, 2.3s < 5.1s, 8.8it/s]
```

**When to Use TQDM:**
- ✅ Batch operations with clear progress (N out of M items)
- ✅ Operations that iterate multiple times with similar latency
- ❌ Single one-off operations
- ❌ Operations with unpredictable completion time

---

## Structured IO Event Logging

### Log Format for Major Operations

Use **START events only** (no END events) to mark major operational phases. Include structured metadata.

**Format:** `Operation START: key1=value1 | key2=value2`

### Scenario Processing

```python
# At start of scenario batch processing
run_logger.info(f"Scenario START: test_subject={test_subject} | variant_id={model_variant}")

# TQDM bar handles per-scenario visibility
# Console output:
# 2026-01-03 14:30:45 [INFO] <oneshot.py:232> Scenario START: test_subject=claude-sonnet | variant_id=v1
```

### Judge Execution

```python
# At start of judge batch execution
run_logger.info(f"Judge START: test_subject={test_subject} | variant_id=subject_agent | judges={len(judges_list)}")

# TQDM bar handles per-scenario/judge visibility
# Console output:
# 2026-01-03 14:35:20 [INFO] <oneshot.py:281> Judge START: test_subject=claude-sonnet | variant_id=subject_agent | judges=1
```

### Judge Individual Results (via judge_executor.py)

```python
# Existing patterns—keep for individual judge logging
logger.info(f"Executing judge '{judge.config.name}' for scenario '{scenario.id}'")
logger.info(f"Judge '{judge.config.name}' scored {result.score}/10 for scenario '{scenario.id}'")

# These are DEBUG-level in log files, not visible in console TQDM context
```

### Configuration & Validation

```python
# Configuration loading
run_logger.debug(f"Loading eval_config.json")
run_logger.debug(f"Loaded {len(scenarios_list)} scenarios")
run_logger.debug(f"Initialized {processor_type} processor")

# Errors
run_logger.error(f"Failed to resolve model for judge '{judge.config.name}': {e}")
run_logger.warning(f"Could not find scenarios file for config hash")
```

---

## Logging Decision Matrix

| Operation | Log Level | Handler | Pattern | Example |
|-----------|-----------|---------|---------|---------|
| Evaluation creation | INFO | app_logger | Direct log | `app_logger.info("Evaluation 'test' created")` |
| Config file loaded | DEBUG | run_logger | Direct log | `run_logger.debug("Loaded eval_config.json")` |
| Scenario batch start | INFO | run_logger | START event | `run_logger.info("Scenario START: test_subject=... \| variant_id=...")` |
| Scenario progress | — | — | TQDM bar | `[45/100, scenario-42 \| claude \| v1]` |
| Judge batch start | INFO | run_logger | START event | `run_logger.info("Judge START: ...")` |
| Judge progress | — | — | TQDM bar | `[8/45, scenario-7 \| claude \| v1]` |
| Judge score (per-judge) | INFO | logger (judge_executor.py) | Direct log | `logger.info("Judge 'quality' scored 8/10")` |
| Validation error | ERROR | run_logger | Direct log with trace | `run_logger.error("Invalid config", exc_info=True)` |
| Result export | DEBUG | run_logger | Direct log | `run_logger.debug("Exporting to results_raw.jsonl")` |

---

## Implementation Guidelines

### For New Features/Workflows

1. **Determine Logging Scope**
   - Application-level event? → Use `get_application_logger()`
   - Run-specific event? → Use `get_run_logger()`

2. **Choose Log Level**
   - `DEBUG`: Implementation details, variable values, intermediate states
   - `INFO`: Major operations, user-facing status, milestones
   - `WARNING`: Recoverable issues, missing optional config
   - `ERROR`: Failures, exceptions (use `exc_info=True`)

3. **For Batch Operations**
   - Log START event at INFO level
   - Use TQDM bar for progress (not DEBUG logs per-item)
   - Describe batch parameters: subject, variant, count

4. **Format Constraints**
   - Use `LOG_FORMAT` from `log_config.py`
   - Structured metadata: `key1=value1 | key2=value2`
   - No newlines in message (single-line logs)
   - File paths as absolute or relative from project root

### Example: New Judge Type

```python
# In judge executor or judge implementation
import logging
from gavel_ai.log_config import get_run_logger

# Get logger based on context
logger = logging.getLogger(__name__)  # For per-judge logs (DEBUG/INFO during execution)
# OR
run_logger = get_run_logger(run_id, eval_name)  # For run-level visibility

# Implementation
logger.info(f"Executing judge '{judge.config.name}' for scenario '{scenario.id}'")
logger.info(f"Judge '{judge.config.name}' scored {result.score}/10")

# If batch: Use TQDM bar in judge_executor.execute_batch() instead of per-item logs
```

### Example: New Configuration Loader

```python
import logging
from gavel_ai.log_config import get_run_logger

run_logger = get_run_logger(run_id, eval_name)

# Configuration events
run_logger.debug("Loading custom_config.yaml")
run_logger.debug(f"Loaded {len(items)} items from custom_config.yaml")

# Validation
if not config.get("required_field"):
    run_logger.error("Missing required field 'required_field' in custom_config.yaml", exc_info=True)
    raise ConfigError(...)
```

---

## Code Changes

### Modified Files

| File | Changes |
|------|---------|
| `src/gavel_ai/log_config.py` | Added console handler to `get_application_logger()` and `get_run_logger()`. Added environment variable support (`LOG_LEVEL_APP`, `LOG_LEVEL_RUN`). |
| `src/gavel_ai/core/executor.py` | Added `test_subject` and `variant_id` parameters. Integrated TQDM progress bar with live description updates. |
| `src/gavel_ai/judges/judge_executor.py` | Added `test_subject` parameter to `execute_batch()`. Integrated TQDM progress bar for judge execution. |
| `src/gavel_ai/cli/workflows/oneshot.py` | Refactored scenario/judge logging to START-only format. Updated executor/judge_executor calls to pass context for TQDM. Removed per-iteration DEBUG logs in favor of TQDM. |
| `.env.example` | Added `LOG_LEVEL_APP` and `LOG_LEVEL_RUN` variables with documentation. |
| `pyproject.toml` | Added `tqdm>=4.65.0` dependency. |

### New Dependencies

```toml
dependencies = [
    # ... existing ...
    "tqdm>=4.65.0",  # Progress bar display for batch operations
]
```

---

## Console Output Examples

### Scenario Processing Run

```
Running evaluation 'test_os'
✓ Loaded 45 scenarios
✓ Initialized prompt_input processor
Executing 45 scenarios...
2026-01-03 14:30:45 [INFO] <oneshot.py:232> Scenario START: test_subject=claude-sonnet | variant_id=v1
Processing scenarios | scenario-43 | claude-sonnet | v1 [45/45, 18.3s < 0.0s, 2.5it/s]
✓ Executed 45 scenarios
Running 1 judges...
2026-01-03 14:35:20 [INFO] <oneshot.py:281> Judge START: test_subject=claude-sonnet | variant_id=subject_agent | judges=1
Running judges | scenario-42 | claude-sonnet | subject_agent [45/45, 8.5s < 0.0s, 5.3it/s]
✓ Completed judging
✓ Generated report: /path/to/report.html

✅ Evaluation complete
   Run ID: run-20260103-143020
   Scenarios: 45
   Judges: 1
   Report: /absolute/path/to/report.html
```

### Log Files (run.log)

```
2026-01-03 14:30:40 [DEBUG] <oneshot.py:125> Loading configuration for evaluation 'test_os'
2026-01-03 14:30:40 [DEBUG] <oneshot.py:129> Loading eval_config.json
2026-01-03 14:30:40 [DEBUG] <oneshot.py:140> Loaded 45 scenarios
2026-01-03 14:30:45 [INFO] <oneshot.py:232> Scenario START: test_subject=claude-sonnet | variant_id=v1
2026-01-03 14:35:20 [INFO] <oneshot.py:281> Judge START: test_subject=claude-sonnet | variant_id=subject_agent | judges=1
2026-01-03 14:35:20 [INFO] <judge_executor.py:106> Executing judge 'quality' for scenario 'scenario-1'
2026-01-03 14:35:22 [INFO] <judge_executor.py:122> Judge 'quality' scored 8.5/10 for scenario 'scenario-1'
...
2026-01-03 14:38:45 [DEBUG] <oneshot.py:424> Generating report to /path/to/report.html
2026-01-03 14:38:46 [DEBUG] <oneshot.py:428> Successfully generated report: /path/to/report.html
```

---

## Rationale

1. **Two-Tier Separation:** App logger is for global lifecycle; run logger for detailed execution traces. Allows independent tuning and reduces noise.

2. **Console Output:** Real-time visibility during long operations without requiring log file inspection. Operators see progress immediately.

3. **Environment Variables:** Enables flexible log verbosity per deployment/environment without code changes.

4. **TQDM Progress Bars:** Cleaner visual feedback than verbose per-item logging. Prevents log spam while maintaining progress visibility.

5. **START-Only Events:** Reduces redundant logging. START event captures operational context; TQDM provides iteration-level detail.

6. **Structured Format:** `key=value | key2=value2` pattern enables parsing and analysis in centralized logging systems (ELK, DataDog, etc.).

---

## Affects

- **Direct Changes:** Core executor, judge executor, CLI workflows, logging configuration
- **Consumer Impact:** All workflows extending `executor.py` or `judge_executor.py` must pass `test_subject` and `variant_id` for TQDM integration
- **New Features:** Guidelines ensure consistent logging across future features
- **Observability:** Improved real-time visibility for operators; cleaner log files for debugging

---

## Backward Compatibility

**Breaking Changes:**
- `Executor.__init__()` now requires optional `test_subject` and `variant_id` parameters (backward compatible with defaults)
- `JudgeExecutor.execute_batch()` now requires optional `test_subject` parameter (backward compatible with default)

**Graceful Fallback:**
- If `test_subject`/`variant_id` not provided, TQDM displays `"unknown"` instead of crashing
- Existing code calling without these parameters continues to work

**Migration for Existing Code:**
```python
# Before
executor = Executor(processor=proc, parallelism=4)

# After (backward compatible, but adds TQDM context)
executor = Executor(
    processor=proc,
    parallelism=4,
    test_subject=test_subject,  # Optional
    variant_id=model_variant,    # Optional
)
```

---

## Testing & Validation

### Test Coverage

1. **Log Level Configuration**
   - ✅ Verify `LOG_LEVEL_APP` env var controls app logger level
   - ✅ Verify `LOG_LEVEL_RUN` env var controls run logger level
   - ✅ Verify defaults to INFO when not set
   - ✅ Verify invalid level names fall back to INFO

2. **Console Output**
   - ✅ App logger writes to stdout
   - ✅ Run logger writes to stdout
   - ✅ File handlers write to expected paths
   - ✅ Format matches `LOG_FORMAT` specification

3. **TQDM Progress Bars**
   - ✅ Executor progress bar displays correct count
   - ✅ Description updates with latest scenario_id, test_subject, variant_id
   - ✅ Judge executor progress bar displays correct count
   - ✅ Description updates with judge execution context

4. **Structured Logging**
   - ✅ START events logged at INFO level
   - ✅ START events include all required fields
   - ✅ Individual judge logs still emitted during execution
   - ✅ Error logs include exc_info traceback

### Acceptance Criteria

- [x] `LOG_LEVEL_APP` and `LOG_LEVEL_RUN` environment variables work as documented
- [x] Console output visible in real-time for both app and run loggers
- [x] TQDM bars display for scenario processing and judge execution
- [x] TQDM description updates with latest scenario/judge/subject/variant info
- [x] All START events follow structured format
- [x] Log files contain all DEBUG and INFO messages
- [x] Code compiles without errors (pytest, mypy pass)
- [x] Backward compatible with existing code

---

## Future Enhancements

1. **Structured Logging Library:** Consider `python-json-logger` for JSON output to centralized logging systems
2. **Metric Correlation:** Link log entries to telemetry spans via trace_id for correlation
3. **Log Aggregation:** CI/CD integration with ELK Stack or Datadog for multi-run analysis
4. **Custom TQDM Handlers:** TqdmLoggingHandler to route logging through TQDM for complete batch operation visibility
5. **Per-Component Verbosity:** Fine-grained control (e.g., `LOG_LEVEL_PROCESSOR=DEBUG`)

---

## References

- **Parent Document:** `logging-vs-telemetry-specification.md` (distinguishes logging from OT spans)
- **Configuration:** `src/gavel_ai/log_config.py` (implementation details)
- **Standards:** Global CLAUDE.md logging preference (LOG_FORMAT standard)
- **Dependencies:** `tqdm` library for progress display

---

## Sign-Off

**Decision Status:** ✅ **APPROVED**
**Implementation Status:** ✅ **COMPLETE**
**Workflow:** Story 7-12 (Chat-driven Enhancement: Logging Improvements)

**Implemented By:** Dev Agent (Amelia)
**Verified By:** Manual testing + code inspection
**Date Completed:** 2026-01-03
