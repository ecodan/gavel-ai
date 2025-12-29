# Story 2.3: Implement Config Loading and Validation

Status: review

## Story

As a developer,
I want configuration files to be loaded and validated at startup,
So that configuration errors are caught early with clear messages.

## Acceptance Criteria

1. **Valid Config Loading:**
   - Given a valid config file exists
   - When it is loaded
   - Then it is parsed and validated using Pydantic with `extra='ignore'`

2. **Missing Required Fields:**
   - Given a config file is missing required fields
   - When it is loaded
   - Then a ConfigError is raised with a clear message explaining what's missing

3. **Forward Compatibility:**
   - Given a config file contains unknown fields
   - When it is loaded
   - Then those fields are silently ignored (forward compatible)

4. **Type Mismatch Handling:**
   - Given a config file has type mismatches
   - When it is loaded
   - Then a ValidationError is raised with guidance on fixing the issue

5. **Environment Variable Substitution:**
   - Given environment variables are referenced (e.g., {{LLM_API_KEY}})
   - When the config is loaded
   - Then environment variables are substituted

## Tasks / Subtasks

- [x] Task 1: Create config module structure (AC: #1)
  - [x] Create `src/gavel_ai/core/config/__init__.py`
  - [x] Create `src/gavel_ai/core/config/loader.py`
  - [x] Create `src/gavel_ai/core/config/models.py`
  - [N/A] Create `src/gavel_ai/core/config/validator.py` (Pydantic handles validation)
  - [N/A] Create `src/gavel_ai/core/config/errors.py` (Using existing exceptions.py)

- [x] Task 2: Implement configuration models (AC: #1, #3)
  - [x] Create EvalConfig Pydantic model with `extra='ignore'`
  - [x] Create AsyncConfig Pydantic model
  - [x] Models use ConfigDict(extra='ignore') for forward compatibility

- [x] Task 3: Implement config loader (AC: #1, #5)
  - [x] Implement JSON file loading
  - [x] Implement YAML file loading
  - [x] Implement TOML file loading (for prompts)
  - [x] Add environment variable substitution ({{VAR}})
  - [N/A] CSV loading (will be handled in Story 2.5 for scenarios)

- [x] Task 4: Implement error handling (AC: #2, #4)
  - [x] ConfigError and ValidationError already exist in exceptions.py
  - [x] Add clear error messages with recovery guidance

- [x] Task 5: Write comprehensive tests
  - [x] Unit tests for each config file type
  - [x] Tests for missing required fields
  - [x] Tests for unknown fields (forward compatibility)
  - [x] Tests for type mismatches
  - [x] Tests for environment variable substitution
  - [x] 15 comprehensive unit tests, all passing

## Dev Notes

### Configuration Files to Support

| File Type | Format | Purpose |
|-----------|--------|---------|
| agents.json | JSON | Agent and model definitions |
| eval_config.json | JSON | Evaluation configuration |
| async_config.json | JSON | Async/concurrency settings |
| judges/*.json | JSON | Judge configurations |
| scenarios.json | JSON | Test scenarios |
| scenarios.csv | CSV | Alternative scenario format |
| prompts/*.toml | TOML | Prompt templates |

### Pydantic Model Pattern (MANDATORY)

**All config models MUST use `extra='ignore'` for forward compatibility:**

```python
from pydantic import BaseModel, ConfigDict

class EvalConfig(BaseModel):
    """Evaluation configuration model."""
    model_config = ConfigDict(extra='ignore')  # Forward compatible

    eval_name: str
    eval_type: str
    processor_type: str
    scenarios_file: str
    agents_file: str
    judges_config: str
    output_dir: str
```

### Environment Variable Substitution

**Pattern:** `{{VAR_NAME}}` in config files

**Example:**
```json
{
  "provider_auth": {
    "api_key": "{{ANTHROPIC_API_KEY}}"
  }
}
```

**Implementation:**
```python
import os
import re

def substitute_env_vars(content: str) -> str:
    """Substitute {{VAR_NAME}} with environment variables."""
    pattern = r"\{\{([A-Z_]+)\}\}"

    def replace(match):
        var_name = match.group(1)
        value = os.getenv(var_name)
        if value is None:
            raise ConfigError(
                f"Environment variable '{var_name}' not set - "
                f"Set {var_name} environment variable or provide value directly"
            )
        return value

    return re.sub(pattern, replace, content)
```

### Config Loader Implementation

```python
from pathlib import Path
from typing import TypeVar, Type
import json
import yaml
import toml

T = TypeVar('T', bound=BaseModel)

def load_config(
    config_path: Path,
    model: Type[T],
    substitute_env: bool = True,
) -> T:
    """Load and validate configuration file."""
    if not config_path.exists():
        raise ConfigError(
            f"Config file not found: {config_path} - "
            f"Create file or check path"
        )

    # Read file content
    content = config_path.read_text()

    # Substitute environment variables
    if substitute_env:
        content = substitute_env_vars(content)

    # Parse based on file extension
    if config_path.suffix == ".json":
        data = json.loads(content)
    elif config_path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(content)
    elif config_path.suffix == ".toml":
        data = toml.loads(content)
    else:
        raise ConfigError(
            f"Unsupported config format: {config_path.suffix} - "
            f"Use .json, .yaml, or .toml"
        )

    # Validate with Pydantic
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ValidationError(
            f"Config validation failed in {config_path} - "
            f"Fix validation errors: {e}"
        )
```

### Error Handling (MANDATORY)

**Exception Hierarchy:**
```python
from gavel_ai.core.exceptions import GavelError

class ConfigError(GavelError):
    """Configuration file errors (missing, invalid format, etc.)."""
    pass

class ValidationError(GavelError):
    """Data validation errors (type mismatch, missing fields, etc.)."""
    pass
```

**Error Message Pattern:**
```python
# Missing required field
raise ConfigError(
    "Missing required field 'agents_file' in eval_config.json - "
    "Add 'agents_file' with path to agents.json"
)

# Type mismatch
raise ValidationError(
    "Field 'max_workers' must be integer, got string - "
    "Change 'max_workers' value to numeric format"
)

# Missing environment variable
raise ConfigError(
    "Environment variable 'ANTHROPIC_API_KEY' not set - "
    "Set ANTHROPIC_API_KEY environment variable or provide value directly"
)
```

### File Structure

```
src/gavel_ai/
├── core/
│   ├── config/
│   │   ├── __init__.py         # Export load_config, models
│   │   ├── loader.py           # Main loading logic
│   │   ├── validator.py        # Validation utilities
│   │   ├── models.py           # All Pydantic config models
│   │   └── errors.py           # ConfigError, ValidationError
│   └── exceptions.py           # GavelError base class
```

### Configuration Models

**EvalConfig:**
```python
class EvalConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')

    eval_name: str
    eval_type: str  # "local" or "in-situ"
    processor_type: str
    scenarios_file: str
    agents_file: str
    judges_config: str
    output_dir: str
```

**AsyncConfig:**
```python
class AsyncConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')

    max_workers: int = 4
    timeout_seconds: int = 30
    retry_count: int = 3
    error_handling: str = "fail_fast"  # or "continue"
```

### Testing Requirements

**Unit Tests** (`tests/unit/test_config_loader.py`):
- Load valid JSON config
- Load valid YAML config
- Load valid TOML config
- Handle missing file (ConfigError)
- Handle invalid JSON/YAML/TOML syntax
- Handle missing required fields (ValidationError)
- Handle unknown fields (silently ignore)
- Handle type mismatches (ValidationError)
- Environment variable substitution
- Missing environment variables (ConfigError)

**Integration Tests** (`tests/integration/test_config_loading.py`):
- Load complete config set (agents, eval, async)
- Load configs from scaffolded evaluation
- Cross-config validation (references between configs)

**Test Coverage:** 70%+ on config loading logic

### Forward Compatibility Strategy

**Why `extra='ignore'`:**
- Future versions can add new fields
- Old code won't break when loading new configs
- Supports gradual migration and rollback

**Example:**
```json
{
  "eval_name": "my_eval",
  "eval_type": "local",
  "new_feature_flag": true  // Added in v2.0, ignored by v1.0
}
```

v1.0 code silently ignores `new_feature_flag` ✅

### Dependencies

**Blocked By:**
- Story 2.2 (Scaffolding) - Generates configs to load

**Blocks:**
- Story 2.4 (Agents Schema) - Needs config loading
- Story 2.5 (Scenarios Schema) - Needs config loading
- Story 2.6 (Judge Schema) - Needs config loading
- Epic 3+ - All execution needs config

**External Dependencies:**
- `pydantic>=2.0` - Schema validation
- `pyyaml` - YAML support
- `toml` - TOML support (for prompts)

### Functional Requirements Mapped

| FR | Requirement | Implementation |
|----|-------------|----------------|
| FR-1.2 | JSON/YAML configuration persistence | Config loader with JSON/YAML support |
| FR-1.6 | Templating and environment variables | {{VAR}} substitution |
| FR-9.6 | Pre-execution validation | Pydantic validation at load time |

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2-Story-3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-2-Code-Standards]
- [Source: _bmad-output/planning-artifacts/project-context.md#Configuration-Format]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

No critical issues encountered during implementation.

### Completion Notes

✅ **Story 2-3 Implementation Complete - 2025-12-28**

**Implementation Summary:**
- Created `src/gavel_ai/core/config/` module with __init__.py, models.py, loader.py
- Implemented EvalConfig and AsyncConfig Pydantic models with `extra='ignore'` for forward compatibility
- Implemented `load_config()` function supporting JSON, YAML, and TOML formats
- Environment variable substitution with {{VAR_NAME}} pattern fully functional
- Used existing ConfigError and ValidationError from exceptions.py (no new errors needed)
- Validation handled by Pydantic (no separate validator.py needed)

**Tests Added:**
- 15 comprehensive unit tests covering all acceptance criteria
- All tests passing (78/78 total suite)
- Test coverage includes:
  - JSON, YAML, TOML loading
  - Missing file error handling
  - Invalid syntax error handling
  - Missing required fields validation
  - Type mismatch validation
  - Forward compatibility (unknown fields ignored)
  - Environment variable substitution
  - Missing environment variable error handling

**Code Quality:**
- All ruff linting checks passed
- All type hints complete
- Error messages follow required pattern: `<Type>: <What> - <How to fix>`
- OpenTelemetry instrumentation on all config loading operations

**Dependencies Added:**
- pyyaml>=6.0 (for YAML support)
- toml>=0.10.0 (for TOML support)

**Architecture Decisions Implemented:**
- All Pydantic models use `ConfigDict(extra='ignore')` for forward compatibility
- Environment variable substitution pattern: `{{VAR_NAME}}`
- Supported formats: .json, .yaml, .yml, .toml
- Telemetry on all config loading operations

### File List

**New Files:**
- `src/gavel_ai/core/config/__init__.py` - Module exports (load_config, EvalConfig, AsyncConfig)
- `src/gavel_ai/core/config/models.py` - Pydantic config models with extra='ignore'
- `src/gavel_ai/core/config/loader.py` - Config loader with env var substitution
- `tests/unit/test_config_loader.py` - 15 comprehensive unit tests

**Modified Files:**
- `pyproject.toml` - Added pyyaml>=6.0 and toml>=0.10.0 dependencies

**Note:** validator.py and errors.py were not created because:
- Validation is handled by Pydantic's model_validate()
- ConfigError and ValidationError already exist in src/gavel_ai/core/exceptions.py

## Change Log

- **2025-12-28:** Story created with comprehensive config loading implementation guide
- **2025-12-28:** Added Pydantic models, environment substitution, error handling patterns
- **2025-12-28:** ✅ Implementation complete - All tasks finished, 78/78 tests passing, all code quality checks passed
