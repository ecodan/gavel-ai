# Story 5.1: Implement Reporter Base Class and Interface

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a clean reporter interface,
So that different report formats can be implemented consistently.

## Acceptance Criteria

- **Given** Reporter ABC is defined
  **When** examined
  **Then** it has:
  - `async generate(run: Run, template: str) -> str` method
  - Support for multiple output formats

**Related Requirements:** FR-6.1

## Tasks / Subtasks

- [x] Create Reporter ABC in src/gavel_ai/reporters/base.py (AC: 1)
  - [x] Define abstract `async generate(run: Run, template: str) -> str` method
  - [x] Add type hints for all parameters and return types
  - [x] Add docstrings following project standards
  - [x] Integrate with OpenTelemetry for span emission

- [x] Create ReporterConfig Pydantic model in src/gavel_ai/core/models.py (AC: 1)
  - [x] Add required fields: template_path (str), output_format (str)
  - [x] Add optional fields: custom_vars (Optional[Dict[str, Any]])
  - [x] Use ConfigDict with extra='ignore' for forward compatibility
  - [x] Add validation for output_format (html, markdown, json)

- [x] Add ReporterError exception to src/gavel_ai/core/exceptions.py (AC: 1)
  - [x] Inherit from GavelError
  - [x] Follow error message format: "<Type>: <What> - <How to fix>"
  - [x] Add docstring explaining when to use

- [x] Write comprehensive unit tests in tests/unit/reporters/test_base.py (AC: 1)
  - [x] Test Reporter ABC cannot be instantiated directly
  - [x] Test concrete implementations must implement generate method
  - [x] Test ReporterConfig validation (valid and invalid cases)
  - [x] Test ReporterError is raised with proper format
  - [x] Achieve 70%+ coverage on reporter base module

- [x] Update __init__.py exports (AC: 1)
  - [x] Export Reporter from src/gavel_ai/reporters/__init__.py
  - [x] Export ReporterConfig from src/gavel_ai/core/models.py
  - [x] Export ReporterError from src/gavel_ai/core/exceptions.py

## Dev Notes

### Architecture Context

This story implements the **Reporter Base Class and Interface**, which is the foundational abstraction for all report generation in gavel-ai. This follows **Architectural Decision 8** (Domain-driven storage abstraction) by establishing clean interfaces that can be extended with different implementations.

**Key Architectural Principles:**
- Clean abstraction architecture (FR-6.1)
- Pluggable report formats (HTML, Markdown, JSON)
- Separated presentation tier (FR-6.5)
- OpenTelemetry instrumentation (Decision 9)

### Implementation Patterns from Previous Work

**From Epic 1-4 Completed Stories:**

1. **Base Class Pattern** (established in Epic 3, Story 3.1):
   - All base classes go in `base.py` files
   - Use ABC with `@abstractmethod` decorators
   - Constructor takes Pydantic config model
   - Initialize tracer with `get_tracer(__name__)`
   - Example: `InputProcessor` in src/gavel_ai/processors/base.py

2. **Config Model Pattern** (established in Epic 2, Story 2.3):
   - All config models use Pydantic with `extra='ignore'`
   - Required fields have no defaults
   - Optional fields use `Optional[Type] = None`
   - Example: `ProcessorConfig` in src/gavel_ai/core/models.py

3. **Exception Pattern** (established in Epic 1, Story 1.5):
   - All exceptions inherit from `GavelError`
   - Follow format: `"<ErrorType>: <What happened> - <Recovery step>"`
   - Example: `ProcessorError`, `JudgeError` in src/gavel_ai/core/exceptions.py

4. **Testing Pattern** (established in Epic 1, Story 1.4):
   - Tests mirror source structure exactly
   - Use pytest fixtures from conftest.py
   - Mock external dependencies (no real API calls)
   - Achieve 70%+ coverage on non-trivial code
   - Example: tests/unit/processors/test_base.py

### Technical Requirements

**Python Code:**
- Python 3.10+ (targeting 3.13)
- All code must use `snake_case` naming
- Complete type hints on all functions and variables
- Async/await pattern (no threading or callbacks)
- All code must pass: black, ruff check, mypy

**Dependencies:**
- No new dependencies for this story
- Uses existing: Pydantic, OpenTelemetry

**File Locations:**
```
src/gavel_ai/reporters/
├── __init__.py           # Export Reporter
├── base.py               # NEW: Reporter ABC

src/gavel_ai/core/
├── models.py             # ADD: ReporterConfig
├── exceptions.py         # ADD: ReporterError

tests/unit/reporters/
├── test_base.py          # NEW: Unit tests
```

### Coding Standards (Absolute Requirements)

From project-context.md:

1. **Naming Conventions:**
   - Functions/variables: `snake_case` (e.g., `async def generate(...)`)
   - Classes: `PascalCase` (e.g., `class Reporter(ABC)`)
   - Constants: `UPPER_SNAKE_CASE` (if any)
   - JSON configs: `snake_case` (not camelCase)

2. **Type Hints:**
   ```python
   # ✅ CORRECT: Complete type hints
   from typing import Optional, Dict, Any
   from abc import ABC, abstractmethod

   class Reporter(ABC):
       def __init__(self, config: ReporterConfig):
           self.config: ReporterConfig = config
           self.tracer = get_tracer(__name__)

       @abstractmethod
       async def generate(self, run: Run, template: str) -> str:
           """Generate report from run data."""
           pass
   ```

3. **Error Handling:**
   ```python
   # ✅ CORRECT: Error message format
   raise ReporterError(
       "Template file not found at config/templates/report.html - "
       "Create template file or check template_path in config"
   )
   ```

4. **Pydantic Config:**
   ```python
   # ✅ CORRECT: Forward-compatible config
   from pydantic import BaseModel, ConfigDict

   class ReporterConfig(BaseModel):
       model_config = ConfigDict(extra='ignore')  # Required

       template_path: str  # Required
       output_format: str  # Required: "html" | "markdown" | "json"
       custom_vars: Optional[Dict[str, Any]] = None  # Optional
   ```

5. **OpenTelemetry:**
   ```python
   # ✅ CORRECT: Span emission pattern
   async def generate(self, run: Run, template: str) -> str:
       with self.tracer.start_as_current_span("reporter.generate") as span:
           span.set_attribute("reporter.type", self.__class__.__name__)
           span.set_attribute("run.id", run.run_id)
           span.set_attribute("output.format", self.config.output_format)
           # Do work
           return output
   ```

### Testing Requirements

**Test Coverage:**
- 70%+ coverage on base.py module
- Unit tests for all public methods
- Mock Run objects (no filesystem access)
- Test error cases and validation

**Test Structure:**
```python
# tests/unit/reporters/test_base.py
import pytest
from gavel_ai.reporters.base import Reporter
from gavel_ai.core.models import ReporterConfig
from gavel_ai.core.exceptions import ReporterError

def test_reporter_abc_cannot_be_instantiated():
    """Reporter ABC cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Reporter(...)

def test_concrete_implementation_must_implement_generate():
    """Concrete implementations must implement generate method."""
    class BadReporter(Reporter):
        pass  # Missing generate()

    with pytest.raises(TypeError):
        BadReporter(...)

def test_reporter_config_validation():
    """ReporterConfig validates required fields."""
    # Valid config
    config = ReporterConfig(
        template_path="templates/report.html",
        output_format="html"
    )
    assert config.template_path == "templates/report.html"

    # Invalid: missing required field
    with pytest.raises(ValidationError):
        ReporterConfig(output_format="html")  # Missing template_path

def test_reporter_error_format():
    """ReporterError follows required format."""
    error = ReporterError(
        "Template not found - Check template_path"
    )
    assert "Template not found" in str(error)
    assert "Check template_path" in str(error)
```

### Project Structure Notes

**Alignment with unified project structure:**
- Follows src-layout strictly (src/gavel_ai/reporters/base.py)
- Base class in dedicated base.py file (not mixed with implementations)
- Tests mirror source structure (tests/unit/reporters/test_base.py)
- Exports managed through __init__.py files

**No conflicts detected.**

### Previous Story Intelligence

**From Epic 4, Story 4.6 (Implement Result Storage):**
- Established pattern for storing results in results.jsonl
- Results include: scenario_id, variant_id, processor_output, judges array
- Reporter will consume these results to generate reports

**From Epic 3, Story 3.1 (Create Processor Base Classes):**
- Established ABC pattern with async methods
- Constructor takes Pydantic config model
- OpenTelemetry integration with get_tracer(__name__)
- **Exact same pattern applies to Reporter ABC**

**From Epic 4, Story 4.1 (Create Judge Base Class):**
- Established pattern for evaluate() method returning typed results
- Similar to Reporter.generate() returning str
- Both use async methods for future extensibility

**Key Learnings:**
- Base classes are simple and focused (single abstract method)
- Config models use extra='ignore' for forward compatibility
- All async methods for consistency (even if not strictly needed yet)
- OpenTelemetry spans emitted immediately (context manager)

### Git Intelligence Summary

**Recent Commits:**
1. `39c02d1` - Document Epic 4 stories (judging & result evaluation)
2. `b01f044` - Complete Epic 3 and Epic 4 implementation
3. `9943dd8` - Complete Epic 1 and Epic 2 implementation
4. `d41abb2` - Complete PRD and product planning
5. `20c17a9` - Add linting and code quality tooling

**Patterns from Recent Work:**
- All code follows black, ruff, mypy standards (pre-commit hooks)
- Consistent ABC pattern across processors, judges
- Complete type hints throughout codebase
- OpenTelemetry integration in all components
- Pydantic config models with extra='ignore'

**Files to Reference:**
- src/gavel_ai/processors/base.py - **Template for Reporter ABC**
- src/gavel_ai/judges/base.py - **Similar async evaluate pattern**
- src/gavel_ai/core/models.py - **Add ReporterConfig here**
- src/gavel_ai/core/exceptions.py - **Add ReporterError here**
- tests/unit/processors/test_base.py - **Test pattern reference**

### Latest Technical Information

**Pydantic v2.x (Current as of 2025):**
- Use `model_config = ConfigDict(extra='ignore')` (not Config class)
- Use `model_validate()` for validation (not parse_obj)
- Type hints are required for validation

**OpenTelemetry Python SDK (Latest):**
- Use `get_tracer(__name__)` for consistent tracer
- Spans emitted via context manager (with statement)
- Immediate emission, no buffering

**Python 3.13:**
- Type hints fully supported
- `async def` and `await` syntax stable
- No breaking changes from 3.10+

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5: Reporting & Analysis]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1: Implement Reporter Base Class and Interface]
- [Source: _bmad-output/planning-artifacts/project-context.md#Naming Conventions]
- [Source: _bmad-output/planning-artifacts/project-context.md#Error Handling & Exceptions]
- [Source: _bmad-output/planning-artifacts/project-context.md#Type Hints & Validation]
- [Source: _bmad-output/planning-artifacts/project-context.md#Telemetry & Instrumentation]
- [Source: _bmad-output/planning-artifacts/project-context.md#Project Structure & Boundaries]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

No debug issues encountered during implementation.

### Completion Notes List

- ✅ Created Reporter ABC in src/gavel_ai/reporters/base.py following InputProcessor and Judge patterns
- ✅ Added ReporterConfig Pydantic model to src/gavel_ai/core/models.py with extra='ignore' for forward compatibility
- ✅ Added ReporterError exception to src/gavel_ai/core/exceptions.py following GavelError hierarchy
- ✅ Wrote 12 comprehensive unit tests in tests/unit/reporters/test_base.py
- ✅ All tests pass (12/12) with 100% coverage on Reporter base module
- ✅ Updated __init__.py exports for reporters module
- ✅ Code passes ruff linting checks
- ✅ Followed all project coding standards (snake_case, type hints, docstrings)
- ✅ OpenTelemetry integration via get_tracer(__name__) pattern
- ✅ All acceptance criteria satisfied

### File List

- src/gavel_ai/reporters/base.py (NEW)
- src/gavel_ai/reporters/__init__.py (MODIFIED)
- src/gavel_ai/core/models.py (MODIFIED - added ReporterConfig)
- src/gavel_ai/core/exceptions.py (MODIFIED - added ReporterError)
- tests/unit/reporters/test_base.py (NEW)

## Change Log

- 2025-12-29: Story created with comprehensive context from epics, architecture, project-context, and previous story intelligence
- 2025-12-29: Implementation complete - all tasks and subtasks finished, all tests passing
