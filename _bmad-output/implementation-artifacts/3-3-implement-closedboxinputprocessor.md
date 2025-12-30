# Story 3.3: Implement ClosedBoxInputProcessor

Status: done

## Story

As a user,
I want to evaluate deployed HTTP endpoints,
So that I can test production systems without accessing internal models.

## Acceptance Criteria

1. **HTTP Endpoint Configuration:**
   - Given ClosedBoxInputProcessor is initialized with endpoint_url
   - When process() is called
   - Then HTTP POST requests are sent to the configured endpoint

2. **Request/Response Handling:**
   - Given inputs are provided
   - When the processor executes
   - Then payloads are sent as JSON with {id, input, metadata} structure

3. **Error Handling:**
   - Given endpoint is unavailable or returns errors
   - When requests fail
   - Then appropriate ProcessorError is raised with recovery guidance

## Tasks / Subtasks

- [x] Task 1: Create ClosedBoxInputProcessor class
  - [x] Inherit from InputProcessor ABC
  - [x] Implement __init__ with endpoint_url and headers parameters
  - [x] Validate endpoint_url is provided
  - [x] Set up httpx.AsyncClient with timeout configuration

- [x] Task 2: Implement HTTP request processing
  - [x] Create JSON payload from Input instances
  - [x] Make POST requests to endpoint_url
  - [x] Extract response from JSON or text
  - [x] Aggregate metadata (latency, status codes)

- [x] Task 3: Implement error handling
  - [x] Handle httpx.ConnectError (endpoint unavailable)
  - [x] Handle httpx.TimeoutException
  - [x] Handle HTTP error status codes (4xx, 5xx)
  - [x] Provide clear error messages with recovery steps

- [x] Task 4: Write comprehensive unit tests (8 tests)
  - [x] Test initialization with endpoint_url
  - [x] Test endpoint_url required validation
  - [x] Test HTTP request execution
  - [x] Test metadata extraction
  - [x] Test error handling for unavailable endpoints
  - [x] Test HTTP error status handling
  - [x] Test custom headers support
  - [x] Test batch processing

- [x] Task 5: Update module exports
  - [x] Export ClosedBoxInputProcessor from processors/__init__.py

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Completion Notes
- ✅ Created ClosedBoxInputProcessor (154 lines)
- ✅ Implemented HTTP endpoint evaluation with httpx
- ✅ Error handling for ConnectError, TimeoutException, HTTP errors
- ✅ 8 comprehensive unit tests (all passing)
- ✅ Telemetry spans with endpoint attributes
- ✅ Updated processors/__init__.py exports

### File List

**New Files:**
- `src/gavel_ai/processors/closedbox_processor.py` (154 lines)
- `tests/unit/test_closedbox_processor.py` (8 tests)

**Modified Files:**
- `src/gavel_ai/processors/__init__.py`

## Change Log

- **2025-12-29**: ✅ Implementation complete - 8 tests passing, all ACs satisfied
