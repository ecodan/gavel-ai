# Story 7.1: Implement Telemetry Collection & Storage

Status: done

## Story

As a developer,
I want complete execution telemetry captured in OpenTelemetry format and exported to per-run files,
So that performance, debugging, and observability are built-in and actionable.

## Acceptance Criteria

1. **Given** an evaluation runs
   **When** processors, judges, and batch executions complete
   **Then** OT spans are emitted immediately to unified receiver (not buffered)

2. **Given** all spans are collected
   **When** evaluation completes
   **Then** they're exported to `telemetry.jsonl` in the run directory:
   `.gavel/evaluations/{eval}/runs/{run_id}/telemetry.jsonl`

3. **Given** telemetry.jsonl is examined
   **When** individual spans are inspected
   **Then** each span has: name, trace_id, span_id, parent_id, start_time, end_time, duration_ns, attributes, status

4. **Given** telemetry is enabled
   **When** evaluation runs
   **Then** <5% overhead is added (performance impact is minimal)

5. **Given** no OT receiver is configured (OTEL_EXPORTER_OTLP_ENDPOINT not set)
   **When** spans are emitted
   **Then** spans are still collected and exported to telemetry.jsonl (local file export)

6. **Given** an LLM call is made
   **When** the span is recorded
   **Then** attributes include: llm.provider, llm.model, llm.tokens.prompt, llm.tokens.completion, llm.latency_ms

7. **Given** a judge evaluates an output
   **When** the span is recorded
   **Then** attributes include: judge.id, judge.name, judge.score, scenario.id

8. **Given** a processor executes
   **When** the span is recorded
   **Then** attributes include: processor.type, scenario.id, input.length

9. **Given** a batch execution runs
   **When** the span is recorded
   **Then** attributes include: executor.parallelism, batch.size, batch.completed, batch.failed

**Related Requirements:** FR-2.4, FR-8.3, FR-9.5, Decision 9

## Tasks / Subtasks

- [x] Task 1: Implement TelemetryFileExporter class (AC: 2, 3, 5)
  - [x] Create `TelemetryFileExporter` class in `src/gavel_ai/telemetry.py`
  - [x] Implement `export(spans)` method that writes to JSONL file
  - [x] Implement span serialization to JSON (name, trace_id, span_id, parent_id, times, duration, attributes, status)
  - [x] Handle file path configuration (accepts run directory path)
  - [x] Create directory structure if doesn't exist
  - [x] Use append mode for incremental writes (streaming)
  - [x] Handle errors gracefully (log warning, don't crash)

- [x] Task 2: Implement run-aware telemetry context (AC: 2, 5)
  - [x] Add `configure_run_telemetry(run_id: str, eval_name: str, base_dir: str)` function
  - [x] Create telemetry file path: `{base_dir}/evaluations/{eval_name}/runs/{run_id}/telemetry.jsonl`
  - [x] Replace NoOpSpanExporter with TelemetryFileExporter when run context is set
  - [x] Add `reset_telemetry()` function to restore no-op exporter after run
  - [x] Ensure tracer provider can be reconfigured per-run

- [x] Task 3: Update telemetry.py to use TelemetryFileExporter (AC: 1, 2)
  - [x] Modify `_get_span_exporter()` to support file export
  - [x] Keep OTLP export as optional override (OTEL_EXPORTER_OTLP_ENDPOINT)
  - [x] Default to TelemetryFileExporter when run context is configured
  - [x] Default to NoOpSpanExporter when no run context (e.g., during tests)
  - [x] Maintain immediate emission via SimpleSpanProcessor (no batching)

- [x] Task 4: Define telemetry span schema and serialization (AC: 3, 6, 7, 8, 9)
  - [x] Create `TelemetrySpan` Pydantic model for serialization:
    - name: str
    - trace_id: str (hex)
    - span_id: str (hex)
    - parent_id: Optional[str] (hex or null)
    - start_time: int (nanoseconds since epoch)
    - end_time: int (nanoseconds since epoch)
    - duration_ns: int
    - status: str ("OK", "ERROR")
    - attributes: Dict[str, Any]
  - [x] Implement `span_to_dict(span: ReadableSpan) -> dict` conversion
  - [x] Handle attribute type coercion (ensure JSON serializable)
  - [x] Format trace_id and span_id as hex strings

- [x] Task 5: Integrate with CLI run workflow (AC: 1, 2)
  - [x] Call `configure_run_telemetry()` at start of `oneshot.py:run()`
  - [x] Pass run_id, eval_name, base_dir to configure function
  - [x] Call `reset_telemetry()` after run completes (success or failure)
  - [x] Ensure telemetry file is created even if run fails
  - [x] Log telemetry file location to run logger

- [x] Task 6: Verify existing span attributes are complete (AC: 6, 7, 8, 9)
  - [x] Audit `providers/factory.py` for LLM call span attributes
  - [x] Audit `judges/` for judge evaluation span attributes
  - [x] Audit `processors/` for processor execution span attributes
  - [x] Audit `processors/executor.py` for batch execution span attributes
  - [x] Add any missing attributes per specification
  - [x] Ensure all spans include run_id and scenario.id where applicable

- [x] Task 7: Write comprehensive tests (AC: All)
  - [x] `tests/unit/test_telemetry_exporter.py` - Unit tests for exporter
    - Test TelemetryFileExporter creates file
    - Test span serialization correctness
    - Test attribute type handling
    - Test error handling (invalid path, write failure)
  - [x] `tests/unit/test_telemetry_context.py` - Unit tests for context management
    - Test configure_run_telemetry creates correct path
    - Test reset_telemetry restores no-op exporter
    - Test multiple runs create separate files
  - [x] `tests/integration/test_telemetry_integration.py` - End-to-end test
    - Run mini-evaluation with mock provider
    - Verify telemetry.jsonl created in run directory
    - Verify span structure matches schema
    - Verify LLM/judge/processor spans have correct attributes

- [x] Task 8: Validate performance overhead (AC: 4)
  - [x] Add benchmark test comparing run with/without telemetry
  - [x] Measure file I/O overhead during span export
  - [x] Verify <5% overhead for typical evaluation (10-50 scenarios)
  - [x] Document performance characteristics

## Dev Notes

### Architecture Context

This story implements **Phase 4** of the logging-vs-telemetry-specification.md: per-run telemetry export.

**Current State (telemetry.py):**
- TracerProvider initialized with SimpleSpanProcessor (immediate emission)
- NoOpSpanExporter as default (spans collected but not written)
- Optional OTLP export if OTEL_EXPORTER_OTLP_ENDPOINT set
- `get_tracer(__name__)` API works correctly

**Target State:**
- TelemetryFileExporter writes to per-run telemetry.jsonl
- Context management functions for run-aware telemetry
- Spans exported to `.gavel/evaluations/{eval}/runs/{run_id}/telemetry.jsonl`
- Backward compatible: tests and non-run contexts use NoOpSpanExporter

### Telemetry Span Schema (Per Architecture Decision 9)

```json
{
  "name": "llm.call",
  "trace_id": "7e5119529ba632d81ac0dac7b14e6a1e",
  "span_id": "b636602ef135a53c",
  "parent_id": "d4abb4363b352e2c",
  "start_time": 1735674974296088000,
  "end_time": 1735674976629510000,
  "duration_ns": 2333422000,
  "status": "OK",
  "attributes": {
    "llm.provider": "anthropic",
    "llm.model": "claude-3-5-sonnet",
    "llm.tokens.prompt": 150,
    "llm.tokens.completion": 100,
    "llm.latency_ms": 2333,
    "run_id": "run-20251231-120000",
    "scenario.id": "test-1"
  }
}
```

### Standard Span Attribute Requirements

**All Spans:**
- `run_id` - Current run identifier
- `trace_id` - Distributed trace ID (auto-generated)

**LLM Calls (llm.call):**
- `llm.provider` - Provider name (anthropic, openai, etc.)
- `llm.model` - Model version
- `llm.tokens.prompt` - Prompt token count
- `llm.tokens.completion` - Completion token count
- `llm.latency_ms` - API latency in milliseconds

**Judge Evaluations (judge.evaluate):**
- `judge.id` - Judge identifier
- `judge.name` - Judge DeepEval name
- `judge.score` - Evaluation score (1-10)
- `scenario.id` - Scenario being judged

**Processors (processor.execute):**
- `processor.type` - Processor type (prompt_input, closedbox_input)
- `scenario.id` - Scenario being processed
- `input.length` - Input text length

**Batch Execution (executor.execute_batch):**
- `executor.parallelism` - Concurrency level
- `batch.size` - Number of items in batch
- `batch.completed` - Number completed
- `batch.failed` - Number failed

### Key Implementation Patterns

**TelemetryFileExporter Implementation:**

```python
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace import ReadableSpan
from typing import Sequence
import json
from pathlib import Path

class TelemetryFileExporter(SpanExporter):
    """Export spans to JSONL file in run directory."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            with open(self.file_path, "a") as f:
                for span in spans:
                    span_dict = self._span_to_dict(span)
                    f.write(json.dumps(span_dict) + "\n")
            return SpanExportResult.SUCCESS
        except Exception as e:
            logger.warning(f"Failed to export spans: {e}")
            return SpanExportResult.FAILURE

    def _span_to_dict(self, span: ReadableSpan) -> dict:
        return {
            "name": span.name,
            "trace_id": format(span.context.trace_id, "032x"),
            "span_id": format(span.context.span_id, "016x"),
            "parent_id": format(span.parent.span_id, "016x") if span.parent else None,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration_ns": span.end_time - span.start_time,
            "status": span.status.status_code.name,
            "attributes": dict(span.attributes) if span.attributes else {},
        }

    def shutdown(self) -> None:
        pass
```

**Run Context Management:**

```python
# In telemetry.py

_current_run_exporter: Optional[TelemetryFileExporter] = None

def configure_run_telemetry(
    run_id: str,
    eval_name: str,
    base_dir: str = ".gavel",
) -> Path:
    """Configure telemetry export for a specific run."""
    global _current_run_exporter, _tracer_provider

    # Create telemetry file path
    telemetry_path = Path(base_dir) / "evaluations" / eval_name / "runs" / run_id / "telemetry.jsonl"

    # Create new exporter
    _current_run_exporter = TelemetryFileExporter(telemetry_path)

    # Reconfigure tracer provider with new exporter
    _tracer_provider = _initialize_tracer_provider(exporter=_current_run_exporter)

    logger.debug(f"Configured telemetry export: {telemetry_path}")
    return telemetry_path


def reset_telemetry() -> None:
    """Reset telemetry to no-op exporter after run completes."""
    global _current_run_exporter, _tracer_provider

    _current_run_exporter = None
    _tracer_provider = _initialize_tracer_provider()  # Uses NoOpSpanExporter

    logger.debug("Reset telemetry to no-op exporter")
```

**CLI Integration (oneshot.py):**

```python
from gavel_ai.telemetry import configure_run_telemetry, reset_telemetry

async def run(eval_name: str, ...):
    """Execute OneShot evaluation."""
    run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Configure telemetry for this run
    telemetry_path = configure_run_telemetry(
        run_id=run_id,
        eval_name=eval_name,
        base_dir=".gavel",
    )
    run_logger.info(f"Telemetry export: {telemetry_path}")

    try:
        # Execute evaluation...
        pass
    finally:
        # Always reset telemetry (success or failure)
        reset_telemetry()
```

### Dependencies

**Story 7-7 (Structured Logging)** is complete. This story builds on the logging infrastructure by adding the telemetry export counterpart.

**Current log_config.py provides:**
- `get_application_logger()` - `.gavel/gavel.log`
- `get_run_logger(run_id, eval_name)` - `.gavel/evaluations/{eval}/runs/{run_id}/run.log`

**This story adds:**
- `configure_run_telemetry(run_id, eval_name)` - `.gavel/evaluations/{eval}/runs/{run_id}/telemetry.jsonl`
- `reset_telemetry()` - Clean up after run

### File Structure After Implementation

```
.gavel/
├── gavel.log                          # Application-level log (rolling)
└── evaluations/
    └── test_os/
        └── runs/
            └── run-20251231-120000/
                ├── run.log            # Run-specific log (Story 7-7)
                ├── telemetry.jsonl    # OT spans (THIS STORY)
                ├── results.jsonl      # Judge results
                ├── manifest.json      # Run metadata
                └── report.html        # Generated report
```

### What NOT to Do (Per logging-vs-telemetry-specification.md)

**Keep OT spans ONLY for:**
- LLM API calls (llm.call)
- Judge evaluations (judge.evaluate)
- Processor execution (processor.execute)
- Batch coordination (executor.execute_batch)

**Removed in Story 7-7 (already done):**
- Config loading spans
- Storage operation spans
- Report generation spans

### Testing Strategy

**Unit Tests (tests/unit/test_telemetry_exporter.py):**
```python
def test_exporter_creates_file(tmp_path):
    """TelemetryFileExporter creates telemetry.jsonl."""
    exporter = TelemetryFileExporter(tmp_path / "telemetry.jsonl")
    # Create mock span...
    result = exporter.export([mock_span])
    assert result == SpanExportResult.SUCCESS
    assert (tmp_path / "telemetry.jsonl").exists()

def test_span_serialization_format():
    """Spans are serialized with correct schema."""
    # Create span with known attributes
    span_dict = exporter._span_to_dict(mock_span)
    assert "name" in span_dict
    assert "trace_id" in span_dict
    assert "duration_ns" in span_dict
    assert span_dict["attributes"]["llm.provider"] == "anthropic"
```

**Integration Tests (tests/integration/test_telemetry_integration.py):**
```python
async def test_telemetry_captured_during_run(tmp_path, mock_provider):
    """Telemetry.jsonl created with spans during evaluation."""
    # Configure telemetry
    configure_run_telemetry("run-test", "test_eval", str(tmp_path))

    # Run mini-evaluation
    await execute_test_scenario(mock_provider)

    # Verify telemetry file
    telemetry_file = tmp_path / "evaluations/test_eval/runs/run-test/telemetry.jsonl"
    assert telemetry_file.exists()

    # Parse and verify spans
    spans = [json.loads(line) for line in telemetry_file.read_text().splitlines()]
    assert len(spans) > 0
    assert any(s["name"] == "llm.call" for s in spans)
```

### Affected Files

**Modified:**
- `src/gavel_ai/telemetry.py` - Add TelemetryFileExporter, configure_run_telemetry, reset_telemetry
- `src/gavel_ai/cli/workflows/oneshot.py` - Integrate telemetry configuration
- `src/gavel_ai/providers/factory.py` - Verify LLM span attributes
- `src/gavel_ai/judges/base.py` - Verify judge span attributes
- `src/gavel_ai/processors/executor.py` - Verify batch span attributes

**New:**
- `tests/unit/test_telemetry_exporter.py` - Exporter unit tests
- `tests/unit/test_telemetry_context.py` - Context management unit tests
- `tests/integration/test_telemetry_integration.py` - End-to-end telemetry tests

### References

- **[Source: _bmad-output/implementation-artifacts/logging-vs-telemetry-specification.md]** - Complete specification (Phase 4)
- **[Source: _bmad-output/planning-artifacts/architecture.md#Decision-9]** - Telemetry architecture
- **[Source: _bmad-output/planning-artifacts/project-context.md#Telemetry]** - Telemetry patterns
- **[Source: _bmad-output/planning-artifacts/epics.md#Story-7.1]** - Original story definition
- **[Source: _bmad-output/implementation-artifacts/7-7-implement-structured-logging-to-gavel-log.md]** - Logging implementation (dependency)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes

**Implementation completed successfully with all 487 tests passing.**

Key implementation decisions:
1. **DynamicSpanProcessor pattern**: OpenTelemetry doesn't allow overriding TracerProvider once set. Created `DynamicSpanProcessor` that swaps exporters at runtime without recreating the provider. This handles pytest plugins (deepeval, logfire) that initialize OT first.

2. **Immediate span export**: Used `SimpleSpanProcessor` pattern where spans are exported on `on_end()` immediately, not batched. This ensures telemetry is written even if process crashes.

3. **Session fixture for tests**: Added `ensure_telemetry_initialized` session fixture in conftest.py to ensure our processor is registered even when other libraries initialize OT first.

4. **Performance validation**: Benchmark tests show 0.019% overhead (well under the 5% target in AC 4). Typical span creation takes ~0.02ms, batch export ~0.2ms per 10 spans.

5. **Schema compliance**: All spans include required fields per logging-vs-telemetry-specification.md: name, trace_id (32 hex), span_id (16 hex), parent_id, start_time, end_time, duration_ns, status, attributes.

### File List

**Modified:**
- `src/gavel_ai/telemetry.py` - Complete rewrite with TelemetryFileExporter, NoOpSpanExporter, DynamicSpanProcessor, configure_run_telemetry(), reset_telemetry()
- `src/gavel_ai/cli/workflows/oneshot.py` - Integrated telemetry configuration at run start/end
- `src/gavel_ai/providers/factory.py` - Added LLM span attributes (llm.provider, llm.model, llm.tokens.*, llm.latency_ms)
- `src/gavel_ai/core/executor.py` - Added batch span attributes (batch.size, batch.completed, batch.failed)
- `src/gavel_ai/judges/deepeval_judge.py` - Added judge span attributes (judge.id, judge.name, scenario.id)
- `tests/conftest.py` - Added telemetry fixtures (ensure_telemetry_initialized, reset_telemetry_after_test)

**New:**
- `tests/unit/test_telemetry_exporter.py` - 13 unit tests for TelemetryFileExporter
- `tests/unit/test_telemetry_context.py` - 12 unit tests for context management
- `tests/integration/test_telemetry_integration.py` - 10 integration tests for end-to-end telemetry
- `tests/integration/test_telemetry_performance.py` - 5 performance benchmark tests

