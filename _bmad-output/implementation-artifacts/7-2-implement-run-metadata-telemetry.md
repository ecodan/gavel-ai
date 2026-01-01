# Story 7.2: Implement Run Metadata Telemetry

Status: completed

## Story

As a user,
I want execution metrics captured (timing, token counts, etc.) after each run,
So that performance can be analyzed and optimized.

## Acceptance Criteria

1. **Given** an evaluation completes
   **When** run_metadata.json is examined
   **Then** it contains:
   - Total duration (seconds)
   - Mean/median/min/max/std processing time per scenario (milliseconds)
   - Total LLM calls and tokens (prompt/completion)
   - Completed/failed scenario count
   - Retry statistics
   - Per-model token counts

2. **Given** the metadata is available
   **When** reports are generated
   **Then** performance metrics are included in the HTML report and formatted clearly

3. **Given** a run completes successfully
   **When** run_metadata.json is written
   **Then** it's saved to `.gavel/evaluations/{eval}/runs/{run_id}/run_metadata.json`

4. **Given** LLM calls are made during a run
   **When** run completes
   **Then** token counts from each LLM call are aggregated correctly per model

5. **Given** scenarios fail or retry
   **When** run_metadata.json is generated
   **Then** retry counts are accurately tracked

**Related Requirements:** FR-9.5, FR-9.8

## Tasks / Subtasks

- [x] Task 1: Define run_metadata.json schema and Pydantic models (AC: 1, 3)
  - [x] Create `RunMetadataSchema` Pydantic model matching spec
  - [x] Create `ScenarioTimingStats` model for scenario-level metrics
  - [x] Create `LLMMetrics` model for LLM call aggregation
  - [x] Ensure fields are JSON-serializable (datetime handling)
  - [x] Add validation for timing values (no negatives, reasonable ranges)

- [x] Task 2: Create RunMetadataCollector class (AC: 1, 4, 5)
  - [x] Create `RunMetadataCollector` class in new `src/gavel_ai/telemetry/metadata.py`
  - [x] Implement `record_scenario_start(scenario_id: str)` to track scenario start time
  - [x] Implement `record_scenario_complete(scenario_id: str, success: bool)` with completion time
  - [x] Implement `record_llm_call(model: str, prompt_tokens: int, completion_tokens: int)` for token tracking
  - [x] Implement `record_retry(scenario_id: str)` to count retry attempts
  - [x] Store all data in instance variables (lists/dicts) for later export

- [x] Task 3: Integrate metadata collection with telemetry module (AC: 1, 4, 5)
  - [x] Export `RunMetadataCollector` from `src/gavel_ai/telemetry/__init__.py`
  - [x] Add `get_metadata_collector()` function to return current collector instance
  - [x] Add `reset_metadata_collector()` function to reset after run
  - [x] Create `global _metadata_collector` instance variable
  - [x] Ensure collector persists across multiple scenarios in same run

- [x] Task 4: Add metadata recording to executor.py (AC: 1, 4, 5)
  - [x] In `Executor.execute_batch()`, record scenario start/complete events
  - [x] Call `metadata_collector.record_scenario_start(scenario_id)` at scenario start
  - [x] Call `metadata_collector.record_scenario_complete(scenario_id, success)` after scenario finishes
  - [x] Call `metadata_collector.record_retry(scenario_id)` each time a retry occurs
  - [x] Pass success status correctly (True if all variants completed without hard failures)

- [x] Task 5: Add token tracking to provider calls (AC: 1, 4)
  - [x] In `src/gavel_ai/providers/factory.py` where `call_agent()` is implemented
  - [x] After LLM call completes, record token counts: `metadata_collector.record_llm_call(model, prompt_tokens, completion_tokens)`
  - [x] Extract token counts from Pydantic-AI response metadata
  - [x] Ensure model name is normalized (e.g., "claude-3-5-sonnet")

- [x] Task 6: Implement metrics aggregation and export (AC: 1, 2)
  - [x] In `RunMetadataCollector`, add `compute_statistics()` method
  - [x] Calculate scenario timing statistics: mean, median, min, max, std dev
  - [x] Aggregate LLM calls by model
  - [x] Total and per-model token counts
  - [x] Completed/failed/retry counts
  - [x] Generate `RunMetadataSchema` instance from collected data

- [x] Task 7: Integrate metadata export with CLI workflow (AC: 2, 3)
  - [x] In `src/gavel_ai/cli/workflows/oneshot.py:run()`, after evaluation completes
  - [x] Call `metadata_collector.compute_statistics()` to generate metadata
  - [x] Write to run directory: `{run_dir}/run_metadata.json`
  - [x] Call `reset_metadata_collector()` after export (in finally block)
  - [x] Log metadata file location to run logger

- [x] Task 8: Update report generation to include metadata (AC: 2)
  - [x] In `src/gavel_ai/reporters/oneshot_reporter.py` (or base reporter)
  - [x] Load `run_metadata.json` from run directory
  - [x] Add performance section to HTML report template (via _extract_performance_metrics)
  - [x] Display scenario timing stats (mean, median, range)
  - [x] Display LLM usage (total calls, tokens per model)
  - [x] Display execution summary (completed/failed, retries)
  - [x] Format as readable table or summary cards

- [x] Task 9: Write comprehensive tests (AC: All)
  - [x] `tests/unit/test_metadata_collector.py` - Unit tests for RunMetadataCollector
    - [x] Test scenario timing calculation
    - [x] Test token aggregation by model
    - [x] Test retry counting
    - [x] Test statistics computation (mean, median, std dev)
    - [x] Test edge cases (single scenario, zero tokens, no retries)
  - [x] `tests/unit/test_metadata_schema.py` - Pydantic model tests
    - [x] Test schema validation
    - [x] Test JSON serialization roundtrip
    - [x] Test invalid data rejection
  - [x] `tests/integration/test_metadata_integration.py` - End-to-end tests
    - [x] Run mock evaluation and verify metadata is collected
    - [x] Verify metadata file exists in run directory
    - [x] Verify all fields are populated correctly
    - [x] Test with multiple scenarios and LLM calls

- [x] Task 10: Validate performance and accuracy (AC: 1)
  - [x] Add benchmark test to verify metadata collection overhead <1%
  - [x] Verify token counts match actual LLM API responses
  - [x] Test timing accuracy (compare against real scenario execution)
  - [x] Document any limitations or approximations

## Dev Notes

### Architecture Context

This story implements **Phase 5** of the logging-vs-telemetry-specification.md: per-run metadata aggregation and metrics.

**Dependencies:**
- Story 7.1 (Implement Telemetry Collection & Storage) - COMPLETED. Uses same telemetry module
- Story 7.7 (Implement Structured Logging) - COMPLETED. Uses same run logging infrastructure

**Current State (pre-implementation):**
- telemetry.py exists with span collection and export to telemetry.jsonl
- Spans include llm.tokens.prompt and llm.tokens.completion attributes
- No aggregated metrics file yet
- No metadata passed to report generation

**Target State:**
- `RunMetadataCollector` class collects timing and token data during run
- Metrics are aggregated after run completes
- run_metadata.json written to run directory with full metrics
- Reports display performance summary from metadata

### Run Metadata Schema (Per Acceptance Criteria)

```json
{
  "run_id": "run-20251231-120000",
  "eval_name": "test_os",
  "start_time_iso": "2025-12-31T12:00:00Z",
  "end_time_iso": "2025-12-31T12:02:00Z",
  "total_duration_seconds": 120,
  "scenario_timing": {
    "count": 10,
    "mean_ms": 2500,
    "median_ms": 2400,
    "min_ms": 1800,
    "max_ms": 3200,
    "std_ms": 450
  },
  "llm_calls": {
    "total": 40,
    "by_model": {
      "claude-3-5-sonnet": 20,
      "gpt-4": 20
    },
    "tokens": {
      "prompt_total": 5000,
      "completion_total": 2000,
      "by_model": {
        "claude-3-5-sonnet": {
          "prompt": 2500,
          "completion": 1000
        },
        "gpt-4": {
          "prompt": 2500,
          "completion": 1000
        }
      }
    }
  },
  "execution": {
    "completed": 10,
    "failed": 0,
    "retries": 2,
    "retry_details": [
      {
        "scenario_id": "scenario-1",
        "retry_count": 1,
        "reason": "timeout"
      }
    ]
  }
}
```

### Standard Span Attributes Already Collected (per Story 7.1)

**LLM Calls (llm.call):**
- `llm.provider` - Provider name
- `llm.model` - Model version
- `llm.tokens.prompt` - Prompt token count
- `llm.tokens.completion` - Completion token count
- `llm.latency_ms` - API latency

**Scenarios (processor.execute, executor.execute_batch):**
- `scenario.id` - Scenario being processed
- `variant.id` - Variant being executed
- `processor.type` - Processor type
- `executor.parallelism` - Concurrency level
- `batch.size` - Number of items in batch

### Implementation Patterns

**MetadataCollector Usage Pattern:**

```python
from gavel_ai.telemetry import get_metadata_collector

# During execution
collector = get_metadata_collector()

# Track scenario timing
collector.record_scenario_start("scenario-1")
# ... process scenario ...
collector.record_scenario_complete("scenario-1", success=True)

# Track LLM calls
collector.record_llm_call("claude-3-5-sonnet", prompt_tokens=150, completion_tokens=100)

# Track retries
collector.record_retry("scenario-1")

# After run completes
metadata = collector.compute_statistics()
write_metadata_json(metadata, run_dir)
```

**File Structure After Implementation:**

```
.gavel/
├── gavel.log                          # Application-level log
└── evaluations/
    └── test_os/
        └── runs/
            └── run-20251231-120000/
                ├── run.log            # Run-specific log (Story 7-7)
                ├── telemetry.jsonl    # OT spans (Story 7-1)
                ├── run_metadata.json  # Metrics (THIS STORY)
                ├── results.jsonl      # Judge results (Story 4-6)
                ├── manifest.json      # Run metadata (Story 6-3)
                └── report.html        # Generated report (Story 5-3)
```

### Timing Calculation Methodology

**Scenario Duration:**
- Start: `record_scenario_start()` called when executor begins scenario
- End: `record_scenario_complete()` called when all variants and judges complete
- Duration = end_time - start_time

**Statistics (Mean, Median, Min, Max, Std Dev):**
- Use scipy.stats or numpy if available, else implement manually
- Statistics computed across all scenarios in run
- Exclude any retries from first scenario record (count separately)

**Token Aggregation:**
- Each LLM call: `record_llm_call(model, prompt_tokens, completion_tokens)`
- By-model totals: sum all tokens for each unique model name
- Total tokens: sum all prompt and completion tokens across all models

### What NOT to Do

**Do NOT:**
- Double-count tokens if an LLM call is retried (record once per actual call)
- Include overhead time from telemetry collection in scenario timing
- Store personally identifiable information in metadata
- Block execution if metadata collection fails (log warning and continue)

**Do:**
- Use ISO 8601 format for timestamps
- Round floating point stats to 1 decimal place
- Preserve all tokens counts for billing/analysis
- Make metadata available for report generation immediately

### Dependencies

**Internal Dependencies:**
- `src/gavel_ai/telemetry/` - Use same module namespace
- `src/gavel_ai/log_config.py` - Use standard logger
- `src/gavel_ai/cli/workflows/oneshot.py` - Integration point

**External Dependencies:**
- `statistics` (standard library) - For mean, median, stdev
- `pydantic` (already required) - For schema validation
- `json` (standard library) - For serialization

### File Structure After Implementation

**Modified:**
- `src/gavel_ai/telemetry/__init__.py` - Export RunMetadataCollector, get_metadata_collector(), reset_metadata_collector()
- `src/gavel_ai/cli/workflows/oneshot.py` - Call metadata export
- `src/gavel_ai/core/executor.py` - Record scenario timing
- `src/gavel_ai/providers/factory.py` - Record token usage
- `src/gavel_ai/reporters/oneshot_reporter.py` - Display metadata in reports

**New:**
- `src/gavel_ai/telemetry/metadata.py` - RunMetadataCollector, RunMetadataSchema, supporting models
- `tests/unit/test_metadata_collector.py` - Unit tests (15+ tests)
- `tests/unit/test_metadata_schema.py` - Schema tests (8+ tests)
- `tests/integration/test_metadata_integration.py` - Integration tests (10+ tests)

### References

- **[Source: _bmad-output/planning-artifacts/epics.md#Story-7.2]** - Original story definition
- **[Source: _bmad-output/implementation-artifacts/7-1-implement-telemetry-collection-and-storage.md]** - Telemetry implementation (dependency)
- **[Source: _bmad-output/implementation-artifacts/7-7-implement-structured-logging-to-gavel-log.md]** - Logging implementation (dependency)
- **[Source: _bmad-output/planning-artifacts/architecture.md#Decision-9]** - Telemetry architecture
- **[Source: _bmad-output/implementation-artifacts/logging-vs-telemetry-specification.md]** - Complete telemetry spec

## Dev Agent Record

### Agent Model Used

Claude Haiku 4.5 (claude-haiku-4-5-20251001)

### Debug Log References

N/A

### Completion Notes

Story 7.2 created through comprehensive analysis workflow:

1. **Story Selection:** Identified 7-2 as FIRST backlog story in Epic 7 (reading sprint-status.yaml in order)
2. **Epic Context:** Loaded Epic 7 definition from epics.md - Observability & Quality epic with 8 stories
3. **Dependency Analysis:** Story 7.1 (Telemetry Collection) already complete and provides span infrastructure
4. **Architecture Review:** Confirmed telemetry module exists with span collection and export
5. **Requirements Synthesis:** Combined ACs from epics.md with architectural patterns and previous story learnings
6. **Schema Definition:** Defined run_metadata.json schema matching FR-9.5 and FR-9.8 requirements
7. **Task Breakdown:** Created 10 detailed tasks covering schema, collection, aggregation, integration, reporting, and testing

**Key Implementation Considerations:**
- Story depends on Story 7.1 completion (telemetry.py span collection)
- Uses same telemetry module namespace for consistency
- Metadata collection must be lightweight (<1% overhead)
- Token counts extracted from Pydantic-AI response metadata
- Metrics aggregated after run completes, not during execution
- Reports must display metadata in user-friendly format

### File List

**New Files to Create:**
- `src/gavel_ai/telemetry/metadata.py` - Metadata collector and schema classes
- `tests/unit/test_metadata_collector.py` - Collector unit tests
- `tests/unit/test_metadata_schema.py` - Schema validation tests
- `tests/integration/test_metadata_integration.py` - End-to-end tests

**Files to Modify:**
- `src/gavel_ai/telemetry/__init__.py` - Export new classes and functions
- `src/gavel_ai/cli/workflows/oneshot.py` - Call metadata export
- `src/gavel_ai/core/executor.py` - Record scenario timing
- `src/gavel_ai/providers/factory.py` - Record token counts
- `src/gavel_ai/reporters/oneshot_reporter.py` - Display metadata in reports
