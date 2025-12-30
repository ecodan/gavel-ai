# Story 4.1: Create Judge Base Class and Interface

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a clean judge interface,
So that different judge implementations can be plugged in consistently.

## Acceptance Criteria

1. **Judge ABC Defined:**
   - Given Judge ABC is defined
   - When examined
   - Then it has:
     - `__init__(config: JudgeConfig)` constructor
     - `async evaluate(scenario: Scenario, subject_output: str) -> JudgeResult` method
     - Tracer setup via `get_tracer(__name__)`

2. **JudgeResult Model Defined:**
   - Given JudgeResult Pydantic model is defined
   - When examined
   - Then it has:
     - `score: int` field (required, range 1-10)
     - `reasoning: Optional[str] = None` field (optional explanation)
     - `evidence: Optional[str] = None` field (optional supporting evidence)
     - `model_config = ConfigDict(extra='ignore')` for forward compatibility

3. **JudgeConfig Model Defined:**
   - Given JudgeConfig Pydantic model is defined
   - When validated
   - Then it uses `extra='ignore'` for forward compatibility
   - And contains judge identification fields (`judge_id`, `deepeval_name`)

## Tasks / Subtasks

- [ ] Task 1: Create judge data models in `src/gavel_ai/core/models.py` (AC: #2, #3)
  - [ ] Define `Scenario` Pydantic model (id, input dict, expected_behavior optional)
  - [ ] Define `JudgeConfig` Pydantic model with `extra='ignore'`
  - [ ] Define `JudgeResult` Pydantic model (score 1-10, optional reasoning/evidence)
  - [ ] Ensure all models follow naming conventions (snake_case fields, PascalCase classes)
  - [ ] Add type hints to all fields
  - [ ] Write unit tests for model validation

- [ ] Task 2: Create Judge abstract base class in `src/gavel_ai/judges/base.py` (AC: #1)
  - [ ] Define `Judge` ABC with required methods
  - [ ] Implement `__init__(config: JudgeConfig)` constructor
  - [ ] Define `async evaluate(scenario: Scenario, subject_output: str) -> JudgeResult` abstract method
  - [ ] Implement tracer setup using `get_tracer(__name__)`
  - [ ] Add comprehensive docstrings
  - [ ] Write unit tests for base class contract

- [ ] Task 3: Create JudgeError exception in `src/gavel_ai/core/exceptions.py` (AC: #1)
  - [ ] Define `JudgeError(GavelError)` for judge evaluation errors
  - [ ] Ensure error messages follow format: `<ErrorType>: <What> - <Recovery step>`
  - [ ] Add docstrings explaining usage
  - [ ] Write unit tests for exception

- [ ] Task 4: Update module exports in `src/gavel_ai/judges/__init__.py` (AC: #1)
  - [ ] Export `Judge` from base.py
  - [ ] Export all judge-related types
  - [ ] Verify no circular imports

- [ ] Task 5: Write comprehensive tests in `tests/unit/test_judges.py` (All ACs)
  - [ ] Test Judge ABC cannot be instantiated directly
  - [ ] Test concrete judge must implement all abstract methods
  - [ ] Test JudgeConfig validates correctly with extra fields ignored
  - [ ] Test JudgeResult creation and validation (score range 1-10)
  - [ ] Test JudgeResult optional fields (reasoning, evidence)
  - [ ] Test tracer is properly initialized
  - [ ] Ensure 70%+ coverage on non-trivial code

- [ ] Task 6: Run validation and quality checks (All ACs)
  - [ ] Run `black src/ tests/` to format code
  - [ ] Run `ruff check src/ tests/` for linting
  - [ ] Run `mypy src/` for type checking
  - [ ] Run `pytest tests/unit/test_judges.py` to verify all tests pass
  - [ ] Ensure pre-commit hooks pass

## Dev Notes

### Architecture Requirements (Decision 5: Judge Integration & Plugin System)

**CRITICAL: DeepEval-native with declarative GEval support**

From Architecture Document (Decision 5):
- Judge references: DeepEval names only with `deepeval.<name>` namespace (e.g., `deepeval.similarity`, `deepeval.faithfulness`)
- Custom Judges: GEval for custom evaluation logic
- Execution Model: Sequential (judge all results with judge A, then B, etc.)
- Score Format: Integer 1-10 scale
- DeepEval Integration: Use DeepEval directly (wrap/adapt their judges)

**Judge Interface Contract:**
```python
class Judge(ABC):
    def __init__(self, config: JudgeConfig):
        self.config = config
        self.tracer = get_tracer(__name__)  # MANDATORY: Use centralized tracer

    async def evaluate(
        self,
        scenario: Scenario,
        subject_output: str,
    ) -> JudgeResult:
        """Score single output against scenario."""
        pass
```

**JudgeResult Schema:**
```python
class JudgeResult(BaseModel):
    model_config = ConfigDict(extra='ignore')

    score: int  # Required: 1-10 integer score
    reasoning: Optional[str] = None  # Optional: explanation
    evidence: Optional[str] = None  # Optional: supporting evidence
```

**JudgeConfig Schema:**
```python
class JudgeConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')

    judge_id: str  # Required: unique identifier
    deepeval_name: str  # Required: e.g., "deepeval.similarity"
    config: Optional[Dict[str, Any]] = None  # Optional: judge-specific config
    config_ref: Optional[str] = None  # Optional: path to external config file
```

### Technology Stack & Versions

**Python Runtime:** 3.10+ (currently 3.13 in .python-version)

**Core Dependencies:**
- **DeepEval** (LLM-as-judge evaluation library)
- **OpenTelemetry** (native observability instrumentation)
- **Pydantic v2** (data validation with `extra='ignore'`)
- **Python typing** (complete type hints required)

**Development Dependencies:**
- Black ≥23.0 (line length 100)
- Ruff ≥0.1 (linting with isort)
- Mypy ≥1.0 (strict type checking)
- pytest ≥7.0

### Naming Conventions (MANDATORY)

**From Project Context Document:**

1. **Python Code:**
   - Functions/modules: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`
   - Private methods: `_single_underscore`
   - Exceptions: `<Concept>Error` (e.g., `JudgeError`)

2. **Pydantic Models:**
   - Class names: `PascalCase` (e.g., `JudgeConfig`, `JudgeResult`)
   - Field names: ALWAYS `snake_case` (NEVER camelCase)
   - Use `model_config = ConfigDict(extra='ignore')` for forward compatibility

3. **Type Hints:**
   - All functions MUST have complete type hints
   - All important variables MUST have type hints
   - Use `Optional[Type] = None` for optional fields

**Example:**
```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any

class JudgeResult(BaseModel):
    model_config = ConfigDict(extra='ignore')  # REQUIRED

    score: int = Field(ge=1, le=10)  # Required, range 1-10
    reasoning: Optional[str] = None  # Optional
    evidence: Optional[str] = None  # Optional
```

### Error Handling Pattern (MANDATORY)

**From Project Context Document:**

All exceptions MUST inherit from `GavelError` hierarchy:
```python
class GavelError(Exception):
    """Base exception for all gavel-ai errors."""
    pass

class JudgeError(GavelError):
    """Judge evaluation errors."""
    pass
```

**Error Message Format (Required):**
```
<ErrorType>: <What happened> - <Recovery step>
```

**Examples:**
```python
raise JudgeError(
    "DeepEval judge 'similarity' failed with score calculation error - "
    "Check scenario input format and ensure expected_output is provided"
)

raise JudgeError(
    "Judge configuration invalid: missing 'deepeval_name' field - "
    "Add 'deepeval_name' to judge config (e.g., 'deepeval.similarity')"
)
```

### Telemetry Pattern (MANDATORY)

**From Architecture Document (Decision 9: Unified OpenTelemetry Integration):**

- **Centralized Tracer:** Use `get_tracer(__name__)` consistently
- **Immediate Emission:** Spans emitted immediately via context manager (NEVER buffered)
- **Standard Attributes:** All spans include run_id, trace_id, judge-specific attributes

**Pattern:**
```python
from gavel_ai.telemetry import get_tracer

class DeepEvalJudge(Judge):
    def __init__(self, config: JudgeConfig):
        self.config = config
        self.tracer = get_tracer(__name__)  # Use module name

    async def evaluate(self, scenario: Scenario, subject_output: str) -> JudgeResult:
        with self.tracer.start_as_current_span("judge.evaluate") as span:
            span.set_attribute("judge.id", self.config.judge_id)
            span.set_attribute("judge.name", self.config.deepeval_name)
            # Perform evaluation
            score = await self._evaluate_with_deepeval(scenario, subject_output)
            span.set_attribute("judge.score", score)
            # Span is recorded immediately upon context exit
            return JudgeResult(score=score, reasoning="...")
```

**Required Span Attributes for Judge Evaluation:**
- `judge.id`: Unique judge identifier from config
- `judge.name`: DeepEval judge name (e.g., "deepeval.similarity")
- `judge.score`: Resulting score (1-10)
- `scenario.id`: Scenario being evaluated
- `variant.id`: Model variant being judged
- `run_id`: Current run identifier

### Project Structure Alignment

**Files to Create/Modify:**
```
src/gavel_ai/
├── core/
│   ├── models.py           # ADD: Scenario, JudgeConfig, JudgeResult
│   └── exceptions.py       # ADD: JudgeError
├── judges/
│   ├── __init__.py         # UPDATE: Export Judge
│   └── base.py             # NEW: Judge ABC

tests/
└── unit/
    ├── test_models.py      # UPDATE: Add Scenario, JudgeConfig, JudgeResult tests
    └── test_judges.py      # NEW: Test Judge contract
```

**Existing Files (From Epic 3):**
- `src/gavel_ai/telemetry.py` - Already has `get_tracer()` function
- `src/gavel_ai/core/exceptions.py` - Already has `GavelError` base
- `src/gavel_ai/core/models.py` - Already has `ProcessorConfig`, `ProcessorResult`, `Input`

### Type Hints & Validation (MANDATORY)

**From Project Context Document:**

1. **Complete Type Hints Required:**
```python
# ✅ CORRECT
async def evaluate(
    self,
    scenario: Scenario,
    subject_output: str,
) -> JudgeResult:
    pass

# ❌ WRONG
async def evaluate(self, scenario, output):  # Missing types
    pass
```

2. **Pydantic Configuration Pattern:**
```python
# ✅ CORRECT: Lenient on unknown fields
from pydantic import BaseModel, ConfigDict, Field

class JudgeResult(BaseModel):
    model_config = ConfigDict(extra='ignore')  # Forward compatible

    score: int = Field(ge=1, le=10)  # Required with validation
    reasoning: Optional[str] = None  # Optional
    evidence: Optional[str] = None  # Optional
```

3. **Score Validation:**
```python
# ✅ CORRECT: Use Pydantic Field validators
from pydantic import Field

class JudgeResult(BaseModel):
    score: int = Field(ge=1, le=10, description="Score from 1-10")
    # Pydantic automatically validates score is between 1 and 10

# ❌ WRONG: Manual validation in constructor
class JudgeResult(BaseModel):
    score: int

    def __init__(self, **kwargs):
        if not 1 <= kwargs['score'] <= 10:
            raise ValueError("Score must be 1-10")
        super().__init__(**kwargs)
```

### Testing Standards

**From Project Context Document:**
- 70%+ coverage on non-trivial code
- Mock DeepEval judges for offline testing
- Unit tests mirror source structure
- Test both valid and invalid score ranges

**Test Structure:**
```python
# tests/unit/test_judges.py
import pytest
from gavel_ai.judges.base import Judge
from gavel_ai.core.models import JudgeConfig, JudgeResult, Scenario

def test_judge_cannot_be_instantiated():
    """Judge ABC cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Judge(JudgeConfig(judge_id="test", deepeval_name="deepeval.similarity"))

def test_judge_result_score_validation():
    """JudgeResult should validate score range 1-10."""
    # Valid scores
    result = JudgeResult(score=1)
    assert result.score == 1

    result = JudgeResult(score=10)
    assert result.score == 10

    # Invalid scores
    with pytest.raises(ValueError):
        JudgeResult(score=0)  # Too low

    with pytest.raises(ValueError):
        JudgeResult(score=11)  # Too high

def test_judge_config_ignores_unknown_fields():
    """JudgeConfig should ignore unknown fields for forward compatibility."""
    config_data = {
        "judge_id": "test",
        "deepeval_name": "deepeval.similarity",
        "unknown_future_field": "value"  # Should be ignored
    }
    config = JudgeConfig(**config_data)
    assert config.judge_id == "test"
    assert config.deepeval_name == "deepeval.similarity"
```

### Previous Story Intelligence

**From Story 3.1 (Create Processor Base Classes and Interface):**
- ✅ Pattern established: Base classes in `base.py`, implementations in separate files
- ✅ Pattern: Use `get_tracer(__name__)` in all base classes
- ✅ Pattern: All Pydantic models use `ConfigDict(extra='ignore')`
- ✅ Pattern: Comprehensive Dev Notes section with architecture, coding standards, anti-patterns
- ✅ Implementation approach: TDD with red-green-refactor cycle
- **Reuse:** `get_tracer()` from `telemetry.py`, `GavelError` from `exceptions.py`

**From Story 3.7 (Implement Retry Logic):**
- ✅ Latest code style: Comprehensive type hints, snake_case everywhere
- ✅ Pattern: All async functions use `async def` and `await`
- ✅ Pattern: Error messages follow strict format: `<Type>: <What> - <How to fix>`
- ✅ Testing pattern: 8 comprehensive unit tests with clear test names

**Key Learnings:**
- Follow exact same Dev Notes structure as Story 3.1 for consistency
- Include comprehensive architecture requirements section
- Document all mandatory patterns and anti-patterns
- Reference specific architecture decisions
- Include code examples for both correct and incorrect patterns
- Create detailed task breakdown with AC references
- Write 10+ unit tests covering all scenarios

### Latest Technical Information

**DeepEval (latest stable):**
- Provides built-in judges: `deepeval.similarity`, `deepeval.faithfulness`, `deepeval.hallucination`, `deepeval.answer_relevancy`
- Supports custom GEval judges for domain-specific evaluation
- Returns scores as floats (convert to 1-10 int scale for consistency)
- Async-compatible for integration with async evaluation pipeline

**Pydantic v2 (latest stable):**
- Use `model_config = ConfigDict(extra='ignore')` instead of deprecated `Config` class
- Use `Field(ge=1, le=10)` for score validation (greater than or equal to 1, less than or equal to 10)
- Field validation is strict by default
- All JSON configs MUST use `snake_case` field names

**OpenTelemetry Python SDK:**
- Use `opentelemetry-api` and `opentelemetry-sdk` packages
- Spans emit immediately via context manager
- Attributes follow dot notation: `judge.id`, `judge.name`, `judge.score`
- Console exporter already configured in `telemetry.py` from Story 1.6

**Python 3.13 Features:**
- Type hints fully supported
- async/await patterns mature
- Pydantic v2 compatible

### Implementation Checklist (MANDATORY)

Before marking any task complete, verify:

- [ ] All code uses `snake_case` for Python, `snake_case` for JSON/Pydantic fields
- [ ] All exceptions inherit from `GavelError` (specifically `JudgeError`)
- [ ] All functions have complete type hints including return type
- [ ] All Pydantic models use `ConfigDict(extra='ignore')`
- [ ] All telemetry spans emitted immediately (context manager)
- [ ] All error messages follow required format
- [ ] Use `get_tracer(__name__)` (no new tracers created)
- [ ] Result objects match defined schemas (JudgeResult with score 1-10)
- [ ] Organization follows src-layout (judges/base.py for ABC)
- [ ] Tests mirror source structure exactly (tests/unit/test_judges.py)
- [ ] No circular imports detected
- [ ] Pre-commit hooks pass (`black`, `ruff`, `mypy`)
- [ ] All async operations use `async def` and `await`
- [ ] Score validation uses Pydantic Field (ge=1, le=10)

### Anti-Patterns to Avoid (CRITICAL)

**From Project Context Document:**

❌ **NEVER** use camelCase in JSON or Pydantic field names (always snake_case)
❌ **NEVER** create new tracers (use `get_tracer(__name__)`)
❌ **NEVER** buffer telemetry spans before export (emit immediately)
❌ **NEVER** use bare except clauses or swallow exceptions
❌ **NEVER** create circular imports between modules
❌ **NEVER** use callbacks or threading (async/await only)
❌ **NEVER** validate in constructors (validate at load time with Pydantic)
❌ **NEVER** use PascalCase for variables or UPPER_CASE for non-constants
❌ **NEVER** omit type hints or return types
❌ **NEVER** hardcode secrets or configuration values
❌ **NEVER** allow scores outside 1-10 range (use Pydantic Field validation)
❌ **NEVER** make reasoning/evidence required (they are optional fields)

### Project Context Reference

**Primary Source:** `_bmad-output/planning-artifacts/project-context.md`
**Architecture Source:** `_bmad-output/planning-artifacts/architecture.md`

**Key Sections:**
- Technology Stack & Versions
- Naming Conventions (MANDATORY)
- Error Handling & Exceptions
- Type Hints & Validation
- Telemetry & Instrumentation
- Project Structure & Boundaries

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5: Judge Integration & Plugin System]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 9: Telemetry & OpenTelemetry Integration]
- [Source: _bmad-output/planning-artifacts/project-context.md#Naming Conventions]
- [Source: _bmad-output/planning-artifacts/project-context.md#Error Handling & Exceptions]
- [Source: _bmad-output/planning-artifacts/project-context.md#Type Hints & Validation]
- [Source: _bmad-output/planning-artifacts/project-context.md#Telemetry & Instrumentation]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4: Judging & Result Evaluation]
- [Source: _bmad-output/implementation-artifacts/3-1-create-processor-base-classes-and-interface.md#Dev Notes]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

## Change Log

- **2025-12-29**: Story created with comprehensive developer guardrails from Architecture, Project Context, Epic 3 patterns, and Judge-specific requirements
- **2025-12-29**: ✅ Implementation verified - 15 tests passing (test_judge_base.py), Judge ABC, JudgeResult, JudgeConfig, Scenario models all complete and tested
