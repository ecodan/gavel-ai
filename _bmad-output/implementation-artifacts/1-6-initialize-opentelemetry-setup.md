# Story 1.6: Initialize OpenTelemetry Setup

Status: review

## Story

As a developer,
I want OpenTelemetry configured and ready for span emission,
So that telemetry instrumentation can be added incrementally.

## Acceptance Criteria

1. **Telemetry Module:**
   - Given telemetry.py exists in src/gavel_ai/
   - When imported
   - Then `get_tracer()` function is available and returns properly configured tracer

2. **Span Emission:**
   - Given a module calls `get_tracer(__name__)`
   - When it emits spans using the tracer
   - Then spans are collected by configured OT receiver

3. **Graceful Degradation:**
   - Given no OT receiver is configured
   - When spans are emitted
   - Then application continues (OT failures don't block execution)

4. **Span Recording:**
   - Given the application runs
   - When completed
   - Then spans have been recorded and are ready for export

## Tasks / Subtasks

- [x] Task 1: Create telemetry.py module (AC: #1)
  - [x] Initialize OpenTelemetry SDK
  - [x] Create get_tracer() function
  - [x] Configure trace provider
  - [x] Add console exporter for development

- [x] Task 2: Test span emission (AC: #2)
  - [x] Create test that calls get_tracer(__name__)
  - [x] Emit test spans
  - [x] Verify spans are recorded
  - [x] Test context propagation

- [x] Task 3: Graceful degradation (AC: #3)
  - [x] Test with no receiver configured
  - [x] Verify application continues without errors
  - [x] Add error handling for OT initialization

- [x] Task 4: Integration with modules (AC: #4)
  - [x] Test tracer works from different modules
  - [x] Verify spans include proper attributes
  - [x] Test span context isolation

### Review Follow-ups (AI Code Review)

- [ ] [MEDIUM] Missing integration test for telemetry - All 20 tests are unit tests; no integration tests verify that `from gavel_ai.telemetry import get_tracer` works from other modules [tests/test_telemetry.py]
- [ ] [LOW] Missing docstring in NoOpSpanExporter - Inline class lacks docstring explaining purpose [src/gavel_ai/telemetry.py:127]
- [ ] [LOW] Hardcoded service version in telemetry - Line 60 hardcodes "service.version": "0.1.0" instead of referencing pyproject.toml or __version__ [src/gavel_ai/telemetry.py:60]

## Dev Notes

### OpenTelemetry Configuration

**Package Requirements:**
- `opentelemetry-api>=1.0`
- `opentelemetry-sdk>=1.0`
- `opentelemetry-exporter-trace-otlp-proto-http` (optional, for OTLP)

**Tracer Setup:**
- Use global trace provider
- Console exporter for development
- Simple processor for immediate emission (NOT buffering)

**Key Functions:**
```python
def get_tracer(name: str) -> Tracer:
    """Get a tracer for the given module."""
    return trace.get_tracer(name)

def start_span(name: str) -> Span context manager:
    """Start a new span with the given name."""
    tracer = get_tracer(__name__)
    return tracer.start_as_current_span(name)
```

### Important: Immediate Emission

From project-context.md:
- OpenTelemetry spans MUST be emitted immediately upon completion
- NEVER buffer spans before export
- Use context managers for automatic span closing
- All spans must include: run_id, trace_id, context-specific attributes

### Error Handling

**Graceful Degradation:**
```python
try:
    tracer.start_as_current_span("operation")
except Exception:
    # Log but don't fail
    logger.warning("OT span emission failed", exc_info=True)
```

## File List

- `src/gavel_ai/telemetry.py` (new)
- `tests/test_telemetry.py` (new)

## Change Log

- **2025-12-28:** Story created with OpenTelemetry initialization module
- **2025-12-28:** Implementation completed and tested
  - ✅ All acceptance criteria met
  - ✅ telemetry.py created with get_tracer() and start_span() functions
  - ✅ OpenTelemetry SDK configured with TracerProvider and SimpleSpanProcessor
  - ✅ Graceful degradation implemented: OTLP (if configured) → Console → No-op fallbacks
  - ✅ Immediate span emission via SimpleSpanProcessor (no buffering)
  - ✅ Error handling prevents OT failures from blocking application
  - ✅ 20 comprehensive test cases covering all scenarios (test_telemetry.py)
  - ✅ All 20 telemetry tests passing
  - ✅ Support for OTEL_EXPORTER_OTLP_ENDPOINT configuration
