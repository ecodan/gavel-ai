---
project_name: 'gavel-ai'
user_name: 'Dan'
date: '2025-12-28'
sections_completed: ['technology_stack', 'naming_conventions', 'error_handling', 'type_hints', 'telemetry', 'project_structure', 'code_organization', 'configuration']
workflow_status: 'complete'
---

# Project Context for AI Agents - gavel-ai

_This file contains critical rules and patterns that AI agents must follow when implementing code in gavel-ai. Focus on unobvious details that prevent implementation mistakes._

---

## Technology Stack & Versions

**Python Runtime:** 3.10+ (targeting 3.10-3.13, currently 3.13)

**Core Dependencies:** Intentionally minimal at runtime
- **Pydantic-AI v1.39.0** (provider abstraction: Claude, GPT, Gemini, Ollama)
- **DeepEval** (LLM-as-judge evaluation)
- **Jinja2** (report templating)
- **OpenTelemetry** (native observability instrumentation)
- **Typer** (CLI framework with hierarchical commands)
- **Rich** (beautiful terminal output)

**Development Dependencies:**
- Black ≥23.0 (code formatting, line length 100)
- Ruff ≥0.1 (fast linting with isort)
- Mypy ≥1.0 (static type checking, lenient on untyped code)
- pytest ≥7.0 (testing framework)
- pre-commit ≥3.0 (git hooks for formatting, linting, type checking)

**Critical Version Constraints:**
- Pydantic-AI v1.39.0 must be used for all provider abstraction (API stable through v2.0)
- Python 3.10 is minimum; 3.13+ strongly recommended
- No strict version pinning on optional dependencies; use latest stable releases
- All code must pass: `black`, `ruff check`, `mypy src/`

---

## Naming Conventions

**MANDATORY: Strict adherence required for all AI agents**

### Python Code (Functions, Variables, Modules)

```python
# ✅ CORRECT: snake_case for functions, variables, modules
def process_inputs(processor_config: ProcessorConfig) -> ProcessorResult:
    max_retries = 3
    timeout_seconds = 30
    processor_name = "prompt_input"
    pass

# ❌ WRONG: camelCase in Python code
def processInputs(processorConfig):  # Never do this
    maxRetries = 3
    timeoutSeconds = 30
    pass
```

### Python Classes & Types

```python
# ✅ CORRECT: PascalCase for classes and exceptions
class InputProcessor(ABC):
    """Base class for input processors."""
    pass

class ProcessorConfig(BaseModel):
    """Configuration model."""
    pass

class ProcessorError(GavelError):
    """Processor execution error."""
    pass

# ❌ WRONG: lowercase or mixed case for classes
class inputProcessor:  # Never do this
    pass

class processor_config:  # Never do this
    pass
```

### Constants

```python
# ✅ CORRECT: UPPER_SNAKE_CASE for constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 30
LOGGER_NAME = "gavel-ai"

# ❌ WRONG: Other cases for constants
max_retries = 3  # If it's not truly constant, use snake_case
MaxRetries = 3   # Never use PascalCase for constants
```

### JSON Configuration Files (ALWAYS snake_case)

```json
{
  "processor_type": "prompt_input",
  "max_workers": 4,
  "timeout_seconds": 30,
  "async_config": {
    "retry_count": 3,
    "error_handling": "fail_fast"
  },
  "judge_config": {
    "judge_id": "similarity",
    "deepeval_name": "deepeval.similarity"
  }
}
```

```json
{
  "processorType": "prompt_input",
  "maxWorkers": 4,
  "timeoutSeconds": 30,
  "asyncConfig": {
    "retryCount": 3
  }
}
```

**❌ NEVER use camelCase in JSON configs. Always snake_case.**

### Telemetry Attributes (snake_case with dot notation)

```python
span.set_attribute("llm.provider", "anthropic")
span.set_attribute("llm.model", "claude-3.5-sonnet")
span.set_attribute("llm.tokens.prompt", 150)
span.set_attribute("llm.tokens.completion", 100)
span.set_attribute("processor.type", "prompt_input")
span.set_attribute("scenario.id", "scenario-5")
span.set_attribute("variant.id", "variant-1")
span.set_attribute("run.id", run_id)
```

### Exception Naming

```python
# ✅ CORRECT: <Concept>Error format
class ProcessorError(GavelError):
    pass

class JudgeError(GavelError):
    pass

class StorageError(GavelError):
    pass

class ConfigError(GavelError):
    pass

# ❌ WRONG: Other exception naming patterns
class ProcessingException:  # Never use Exception suffix
    pass

class processor_error:  # Never use lowercase
    pass
```

---

## Error Handling & Exceptions

**MANDATORY: All errors use GavelError hierarchy with specific message format**

### Exception Hierarchy (Required)

```python
class GavelError(Exception):
    """Base exception for all gavel-ai errors."""
    pass

class ConfigError(GavelError):
    """Configuration-related errors (file, syntax, validation)."""
    pass

class ProcessorError(GavelError):
    """Processor execution errors (API call, timeout, etc.)."""
    pass

class JudgeError(GavelError):
    """Judge evaluation errors."""
    pass

class StorageError(GavelError):
    """Storage operation errors (file I/O, etc.)."""
    pass

class ValidationError(GavelError):
    """Data validation errors (scenario format, etc.)."""
    pass
```

**All custom exceptions MUST inherit from GavelError or one of its subclasses.**

### Error Message Format (Required)

Every error message MUST follow this pattern:
```
<ErrorType>: <What happened> - <Recovery step>
```

```python
# ✅ CORRECT: Clear, actionable error messages
raise ConfigError(
    "Missing required field 'agents' in agents.json - "
    "Add 'agents' array with at least one provider configuration"
)

raise ProcessorError(
    "LLM API call timed out after 30s - "
    "Increase timeout_seconds in async_config.json or check provider status"
)

raise StorageError(
    "Cannot write to runs directory - "
    "Check disk space and ensure directory permissions allow writing"
)

# ❌ WRONG: Vague or incomplete error messages
raise ConfigError("Invalid config")
raise ProcessorError("Error")
raise StorageError("IO error")
```

### Error Handling in Async Code

```python
# ✅ CORRECT: Specific error handling with chaining
async def process(self, inputs: List[Input]) -> ProcessorResult:
    try:
        result = await self.llm_call(input)
    except TimeoutError as e:
        raise ProcessorError(
            f"LLM call timed out after {self.config.timeout_seconds}s - "
            f"Check provider status or increase timeout"
        ) from e
    except ValueError as e:
        raise ValidationError(
            f"Invalid input format: {e} - Check scenario structure"
        ) from e
    except Exception as e:
        raise ProcessorError(
            f"Unexpected error during processing: {e} - "
            f"Check logs for details"
        ) from e

# ❌ WRONG: Bare except clauses or swallowing errors
try:
    result = await self.llm_call(input)
except:  # Never do this
    pass

except Exception:  # Never swallow without re-raising
    logger.error("error")
```

### Logging Errors

```python
# ✅ CORRECT: Always log with traceback
try:
    process_data()
except ProcessorError as e:
    logger.error(f"Processor error: {e}", exc_info=True)
    raise

# ❌ WRONG: Logging without context
except Exception as e:
    logger.error(str(e))
    raise
```

---

## Type Hints & Validation

**MANDATORY: Complete type hints on all functions and variables. No exceptions.**

### Function Type Hints (Required)

```python
# ✅ CORRECT: Complete type hints
from typing import List, Optional, Dict, Any
from gavel_ai.core.models import ProcessorConfig, ProcessorResult

async def process(
    self,
    inputs: List[Input],
    config: Optional[ProcessorConfig] = None,
) -> ProcessorResult:
    """Process inputs and return results."""
    output: str = await self._execute(inputs)
    metadata: Dict[str, Any] = {"count": len(inputs)}
    return ProcessorResult(output=output, metadata=metadata)

# ❌ WRONG: Missing type hints
async def process(self, inputs):  # Missing return type and parameter type
    output = await self._execute(inputs)
    return ProcessorResult(...)

def execute(inputs, timeout=30):  # Missing all type hints
    pass
```

### Variable Type Hints (Required)

```python
# ✅ CORRECT: Type hints on important variables
max_retries: int = 3
timeout_seconds: float = 30.0
processor_config: ProcessorConfig = ProcessorConfig(...)
results: List[ProcessorResult] = []
metadata: Optional[Dict[str, Any]] = None

# ❌ WRONG: Missing type hints on variables
max_retries = 3  # Should have type hint
processor_config = ProcessorConfig(...)  # Should have type hint
results = []  # Should have List[ProcessorResult] hint
```

### Pydantic Model Validation (Load-Time Only)

```python
# ✅ CORRECT: Validate at load time
raw_config = json.load(open("config.json"))
config = ProcessorConfig.model_validate(raw_config)
# Now config is guaranteed to be valid

# Use validated config throughout
processor = PromptInputProcessor(config)

# ❌ WRONG: Runtime validation or missing validation
config = ProcessorConfig(**raw_config)  # No validation
processor = PromptInputProcessor(config)

# ❌ WRONG: Validating in constructor
class MyProcessor:
    def __init__(self, config_dict):
        self.config = ProcessorConfig(**config_dict)  # Too late
```

### Optional Fields & Defaults

```python
# ✅ CORRECT: Optional fields with None defaults
from typing import Optional

class ProcessorResult(BaseModel):
    output: str  # Required
    metadata: Optional[Dict[str, Any]] = None  # Optional
    error: Optional[str] = None  # Optional

class JudgeResult(BaseModel):
    score: int  # Required: 1-10
    reasoning: Optional[str] = None  # Optional
    evidence: Optional[str] = None  # Optional

# ❌ WRONG: Optional without None default
class ProcessorResult(BaseModel):
    output: str
    metadata: Optional[Dict[str, Any]]  # Missing = None
    error: Optional[str]  # Missing = None
```

### Pydantic Configuration Pattern

```python
# ✅ CORRECT: Lenient on unknown fields
from pydantic import BaseModel, ConfigDict

class ProcessorConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')  # Forward compatible

    processor_type: str  # Required
    parallelism: int = 1  # Optional with default
    timeout_seconds: int = 30  # Optional with default
    metadata: Optional[Dict[str, Any]] = None  # Optional

# ✅ CORRECT: Strict validation when needed
class StrictConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')  # Fail on unknowns

    processor_type: str
    parallelism: int

# ❌ WRONG: No extra field configuration
class ProcessorConfig(BaseModel):
    processor_type: str
    # Unknown fields will cause validation error if strict
```

---

## Telemetry & Instrumentation

**MANDATORY: OpenTelemetry spans emitted immediately upon completion. Never buffer.**

### Centralized Tracer Setup

```python
# ✅ CORRECT: Use centralized get_tracer(__name__)
from gavel_ai.telemetry import get_tracer

class PromptInputProcessor(InputProcessor):
    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.tracer = get_tracer(__name__)  # Use module name

    async def process(self, inputs: List[Input]) -> ProcessorResult:
        with self.tracer.start_as_current_span("processor.execute") as span:
            # Do work
            # Span is recorded immediately upon context exit
            return ProcessorResult(...)

# ❌ WRONG: Creating new tracers in different modules
from opentelemetry import trace

class PromptInputProcessor:
    def __init__(self):
        self.tracer = trace.get_tracer("processor")  # Wrong: creates new tracer

class Judge:
    def __init__(self):
        self.tracer = trace.get_tracer("judge")  # Wrong: inconsistent tracer
```

### Span Emission (Immediate, Not Buffered)

```python
# ✅ CORRECT: Emit span immediately when event occurs
def process(self, inputs: List[Input]) -> ProcessorResult:
    with self.tracer.start_as_current_span("processor.execute") as span:
        span.set_attribute("processor.type", self.config.processor_type)
        span.set_attribute("input.count", len(inputs))

        # Do work here
        output = execute_processing()

        # Span is recorded immediately upon context exit
        return ProcessorResult(output=output)

# ❌ WRONG: Buffering spans for later export
spans = []

def collect_span(name: str):
    span = create_span(name)
    spans.append(span)  # WRONG: Don't buffer

# Later...
def export_all():
    for span in spans:
        exporter.export(span)  # WRONG: Don't batch like this
```

### Standard Span Attributes (All Spans Must Include)

```python
# ✅ CORRECT: All spans include context attributes
with self.tracer.start_as_current_span("processor.execute") as span:
    # Always include these
    span.set_attribute("run_id", run.run_id)
    span.set_attribute("trace_id", trace_id)

    # Plus context-specific attributes:

    # For processor spans:
    span.set_attribute("processor.type", "prompt_input")
    span.set_attribute("scenario.id", scenario_id)
    span.set_attribute("variant.id", variant_id)

    # For judge spans:
    span.set_attribute("judge.id", judge_config.id)
    span.set_attribute("judge.name", "deepeval.similarity")
    span.set_attribute("judge.score", 8)

    # For LLM call spans:
    span.set_attribute("llm.provider", "anthropic")
    span.set_attribute("llm.model", "claude-3.5-sonnet")
    span.set_attribute("llm.tokens.prompt", 150)
    span.set_attribute("llm.tokens.completion", 100)
    span.set_attribute("llm.latency_ms", 2333)

# ❌ WRONG: Incomplete span attributes
with self.tracer.start_as_current_span("processor.execute") as span:
    span.set_attribute("type", "processor")  # Too vague
    # Missing: run_id, trace_id, context-specific attributes
```

### Telemetry Collection Architecture

```
Processors      -> |
Judges          -> | Unified OT Receiver -> File Exporter -> telemetry.jsonl
In-Situ Systems -> |

Key Rule: Single receiver, immediate emission, no per-component collectors
```

**Important:** All telemetry flows to ONE unified receiver. Do not create per-component collectors or batch before export.

---

## Project Structure & Boundaries

**MANDATORY: Strict adherence to src-layout and module organization**

### Directory Structure (Required Layout)

```
src/gavel_ai/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py              # Typer CLI factory (entry point)
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── oneshot.py       # OneShot workflow commands
│   │   ├── conv.py          # Conversational workflow
│   │   └── autotune.py      # Autotune workflow
│   └── common.py            # Shared CLI utilities
├── core/
│   ├── __init__.py
│   ├── models.py            # Pydantic data models
│   ├── config.py            # Config loading and validation
│   ├── exceptions.py        # Exception hierarchy
│   └── types.py             # Type aliases and protocols
├── processors/
│   ├── __init__.py
│   ├── base.py              # InputProcessor ABC
│   ├── prompt_processor.py  # PromptInputProcessor
│   ├── closedbox_processor.py  # ClosedBoxInputProcessor
│   ├── scenario_processor.py   # ScenarioProcessor
│   └── executor.py          # Executor orchestration
├── judges/
│   ├── __init__.py
│   ├── base.py              # Judge ABC
│   ├── deepeval_judge.py    # DeepEval adapter
│   └── registry.py          # Judge registry
├── storage/
│   ├── __init__.py
│   ├── base.py              # Run, Config, Prompt ABCs
│   ├── run.py               # LocalFilesystemRun implementation
│   ├── config.py            # LocalFileConfig implementation
│   └── prompt.py            # LocalFilePrompt implementation
├── reporters/
│   ├── __init__.py
│   ├── base.py              # Reporter ABC
│   ├── jinja_reporter.py    # Jinja2 reporter
│   └── templates/           # HTML/Markdown templates
├── telemetry.py             # OpenTelemetry setup
└── log_config.py            # Logging configuration

tests/
├── conftest.py              # pytest fixtures
├── unit/                    # Unit tests (mirror src/)
├── integration/             # Integration tests
└── fixtures/                # Test data and mocks
```

**Critical Rules:**
- Base classes go in `base.py` (one per module)
- Implementations are explicit: `prompt_processor.py` not `processor.py`
- Tests mirror source structure exactly
- No random files or modules in unexpected places

### Architectural Boundaries (Strict Separation)

```
CLI Boundary:
  - All CLI logic in cli/ module
  - Cannot import from processors, judges, storage (one-way dependency)
  - HTTP API can be added later without touching business logic

Processor Boundary:
  - InputProcessor base class defines interface
  - All implementations inherit from InputProcessor
  - Pydantic-AI abstraction handles provider details
  - Cannot import from CLI directly

Judge Boundary:
  - Judge base class defines interface
  - DeepEval integration in deepeval_judge.py
  - Registry handles judge instantiation
  - Cannot import from CLI directly

Storage Boundary:
  - Abstract base classes: Run, Config, Prompt
  - LocalFilesystemRun is v1 implementation
  - Future: S3, Database, ExperimentTracking without core changes
  - All domain objects know how to persist themselves

Telemetry Boundary:
  - Centralized get_tracer(__name__) in all modules
  - Single OT receiver collects from all sources
  - No per-component collectors or batching before export
  - All spans have consistent attributes
```

### Module Initialization (__init__.py)

```python
# ✅ CORRECT: Export public API, import for convenience
# src/gavel_ai/processors/__init__.py
from gavel_ai.processors.base import InputProcessor
from gavel_ai.processors.prompt_processor import PromptInputProcessor
from gavel_ai.processors.closedbox_processor import ClosedBoxInputProcessor

__all__ = ["InputProcessor", "PromptInputProcessor", "ClosedBoxInputProcessor"]

# Usage:
from gavel_ai.processors import PromptInputProcessor  # Clean import

# ❌ WRONG: Circular imports or wildcard exports
from gavel_ai.processors.base import *  # Never use wildcard
from gavel_ai.cli import main  # Circular: cli imports processors
```

---

## Code Organization & Anti-Patterns

**MANDATORY: Async/await patterns, no callbacks, no circular imports**

### Async/Await Pattern (Required)

```python
# ✅ CORRECT: Use async/await throughout
async def process(self, inputs: List[Input]) -> ProcessorResult:
    """Process inputs asynchronously."""
    tasks = [self._process_single(input) for input in inputs]
    results = await asyncio.gather(*tasks)
    return ProcessorResult(output=results)

async def _process_single(self, input: Input) -> str:
    """Process a single input."""
    response = await self.llm.generate(input.text)
    return response.text

# Usage:
result = await processor.process(inputs)

# ❌ WRONG: Threading or callbacks
def process(self, inputs, callback):  # Never use callbacks
    thread = Thread(target=self._process_thread, args=(inputs, callback))
    thread.start()

def _process_thread(self, inputs, callback):  # Wrong: threading
    result = self._process_blocking(inputs)
    callback(result)
```

### No Circular Imports (Required)

```
# ✅ CORRECT: One-way dependencies
cli/main.py
  ↓ imports from
core/models.py ← processors/ ← storage/

# ❌ WRONG: Circular dependencies
cli/main.py ↔ processors/base.py  (Never)
core/config.py ↔ storage/run.py   (Never)
```

**How to avoid:**
1. Base classes go in separate modules (base.py)
2. CLI only imports from core, processors, judges, storage (one-way)
3. Processors can import from core, storage, judges
4. Don't import from parent or sibling modules

### Base Classes in Dedicated Modules

```python
# ✅ CORRECT: Base classes in base.py
# src/gavel_ai/processors/base.py
from abc import ABC, abstractmethod
from typing import List

class InputProcessor(ABC):
    """Base class for all input processors."""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def process(self, inputs: List[Input]) -> ProcessorResult:
        """Process inputs and return results."""
        pass

# src/gavel_ai/processors/prompt_processor.py
from gavel_ai.processors.base import InputProcessor

class PromptInputProcessor(InputProcessor):
    """Implementation for prompt processing."""

    async def process(self, inputs: List[Input]) -> ProcessorResult:
        # Implementation
        pass

# ❌ WRONG: Base class in same file as implementation
# src/gavel_ai/processors/prompt_processor.py
class InputProcessor(ABC):  # Wrong: should be in base.py
    pass

class PromptInputProcessor(InputProcessor):
    pass
```

### Function and Method Size

```python
# ✅ CORRECT: Single responsibility, readable length
async def process(self, inputs: List[Input]) -> ProcessorResult:
    """Process inputs with error handling and telemetry."""
    with self.tracer.start_as_current_span("processor.execute") as span:
        span.set_attribute("processor.type", self.config.processor_type)

        try:
            results = await self._process_batch(inputs)
            return ProcessorResult(output=results)
        except TimeoutError as e:
            raise ProcessorError(f"Processing timeout - Check provider status") from e

# ❌ WRONG: God methods doing too much
async def process(self, inputs, config=None, validate=True, retry=3, timeout=30):
    # 200+ lines doing multiple things
    # Error handling scattered
    # Telemetry mixed with business logic
    # Difficult to test
    pass
```

### Private Methods (Protected vs Private)

```python
# ✅ CORRECT: Single underscore for protected (internal use)
class InputProcessor:
    async def process(self, inputs: List[Input]) -> ProcessorResult:
        """Public method."""
        return await self._validate_and_process(inputs)  # Protected

    async def _validate_and_process(self, inputs: List[Input]) -> ProcessorResult:
        """Internal method, can be overridden in subclass."""
        validated = self._validate_inputs(inputs)
        return await self._execute(validated)

    async def _validate_inputs(self, inputs: List[Input]) -> List[Input]:
        """Internal helper."""
        pass

# ❌ WRONG: Double underscore (name mangling) or all public
class InputProcessor:
    async def process(self, inputs):
        return await self.__validate_and_process(inputs)  # Wrong: name mangling

    async def validate_inputs(self, inputs):  # Wrong: public when should be protected
        pass
```

### Imports Organization

```python
# ✅ CORRECT: Organized imports at top
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import asyncio

from pydantic import BaseModel, ConfigDict

from gavel_ai.core.models import ProcessorConfig, ProcessorResult
from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.telemetry import get_tracer

class MyProcessor(ABC):
    pass

# ❌ WRONG: In-method imports or disorganized
class MyProcessor:
    def process(self):
        from gavel_ai.core.models import ProcessorConfig  # Import in method
        # Only justified if circular import risk or rarely used
        pass

from gavel_ai.core.models import ProcessorConfig
import asyncio
from abc import ABC
from typing import List  # Scattered imports
```

---

## Configuration & Startup

**MANDATORY: Pydantic validation at load time, environment variable support**

### Config Loading Pattern (Required)

```python
# ✅ CORRECT: Validate at load time
import json
from gavel_ai.core.models import ProcessorConfig, EvalConfig

# Load and validate immediately
with open("config/eval_config.json") as f:
    raw_config = json.load(f)

# Validation happens here
eval_config = EvalConfig.model_validate(raw_config)

# Now config is guaranteed valid throughout the application
processor = PromptInputProcessor(eval_config.processor_config)

# ❌ WRONG: Lazy validation or missing validation
raw_config = json.load(open("config.json"))
eval_config = EvalConfig(**raw_config)  # Might fail later
processor = PromptInputProcessor(eval_config)  # No validation guarantee

# ❌ WRONG: Validating in constructors
class MyClass:
    def __init__(self, config_dict):
        self.config = ProcessorConfig.model_validate(config_dict)  # Too late
```

### Environment Variable Support

```python
# ✅ CORRECT: Use environment variables for secrets and paths
import os
from pydantic import BaseModel, Field

class Config(BaseModel):
    api_key: str = Field(default_factory=lambda: os.getenv("GAVEL_API_KEY", ""))
    eval_root: str = Field(default_factory=lambda: os.getenv("GAVEL_ROOT", ".gavel"))
    debug: bool = Field(default_factory=lambda: os.getenv("GAVEL_DEBUG", "false").lower() == "true")

# Usage:
# $ GAVEL_API_KEY=sk-... GAVEL_ROOT=/custom/path python -m gavel_ai

# ❌ WRONG: Hardcoded secrets
config = Config(api_key="sk-hardcoded-secret")  # Never hardcode

# ❌ WRONG: Accessing environment in business logic
def process(inputs):
    api_key = os.getenv("API_KEY")  # Wrong: should be in config
    pass
```

### Lenient Configuration (Forward Compatible)

```python
# ✅ CORRECT: Accept unknown fields, ignore them
from pydantic import ConfigDict

class ProcessorConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')  # Important for forward compat

    processor_type: str
    parallelism: int = 1
    # If config.json adds 'future_field', it's silently ignored

# ✅ CORRECT: Strict when needed
class StrictConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')  # Fail on unknown fields

    required_field: str
    # config.json with unknown fields will raise ValidationError

# ❌ WRONG: No extra field configuration (defaults to strict in Pydantic v2)
class Config(BaseModel):
    processor_type: str
    # Unknown fields will cause validation error
```

### Required vs Optional Fields

```python
# ✅ CORRECT: Clear required vs optional
class ProcessorConfig(BaseModel):
    # Required fields (no default)
    processor_type: str

    # Optional with defaults
    parallelism: int = 1
    timeout_seconds: int = 30

    # Optional without default (None)
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

# ❌ WRONG: Unclear defaults
class ProcessorConfig(BaseModel):
    processor_type: str
    parallelism: int  # Is this required? Unclear
    timeout_seconds: Optional[int]  # Missing default = None
    metadata: Optional[Dict[str, Any]]  # Missing default = None
```

---

## Critical Rules Summary

### Must Follow (Absolute Requirements)

1. **Naming:** `snake_case` for Python, ALWAYS `snake_case` for JSON (never camelCase)
2. **Exceptions:** All inherit from `GavelError` with format: `<Type>: <What> - <How to fix>`
3. **Type Hints:** Every function and important variable must have complete type hints
4. **Validation:** Use Pydantic at load time only (not in constructors)
5. **Telemetry:** Spans emitted immediately via context manager, never buffered
6. **Tracer:** Use `get_tracer(__name__)` consistently, never create new tracers
7. **Structure:** src-layout strictly enforced, no circular imports
8. **Async:** Use `async def`/`await`, never callbacks or threading
9. **Configs:** `extra='ignore'` for forward compatibility, required fields explicit
10. **Testing:** 70%+ coverage on non-trivial code, mock providers for offline testing

### Code Quality Gates

- `black src/ tests/` — All code formatted
- `ruff check src/ tests/` — All linting passes
- `mypy src/` — All type hints validated
- `pytest` — All tests pass with 70%+ coverage on non-trivial code
- `pre-commit run --all-files` — All hooks pass

### Anti-Patterns to Avoid

❌ Using camelCase in JSON or Python code
❌ Creating new tracers instead of using `get_tracer(__name__)`
❌ Buffering telemetry spans before export
❌ Bare except clauses or swallowing exceptions
❌ Importing from parent/sibling modules (circular imports)
❌ Using callbacks or threading (async/await only)
❌ Validating in constructors instead of at load time
❌ PascalCase for variables or UPPER_CASE for non-constants
❌ Functions without type hints or return types
❌ Hardcoding secrets or configuration values

---

## Implementation Checklist

When implementing any component, verify:

- [ ] All code uses `snake_case` for Python, `snake_case` for JSON
- [ ] All exceptions inherit from `GavelError` or subclass
- [ ] All functions have complete type hints including return type
- [ ] All configs use Pydantic with `extra='ignore'`
- [ ] All telemetry spans emitted immediately (context manager)
- [ ] All error messages follow required format
- [ ] No new tracers created (use `get_tracer(__name__)`)
- [ ] Result objects match defined schemas (ProcessorResult, JudgeResult)
- [ ] Organization follows src-layout (no random files)
- [ ] Tests mirror source structure exactly
- [ ] No circular imports detected
- [ ] Pre-commit hooks pass (`black`, `ruff`, `mypy`)
- [ ] All async operations use `async def` and `await`

---

**Document Version:** 1.0
**Last Updated:** 2025-12-28
**Generated by:** Generate Project Context Workflow

This is the single source of truth for implementation consistency in gavel-ai. All AI agents must follow these rules without exception.
