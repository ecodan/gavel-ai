# Story 2.6: Implement Judge Configuration Schema

Status: review

## Story

As a user,
I want to configure DeepEval judges (built-in and custom GEval) in eval_config.json,
So that I can define evaluation criteria without modifying code.

## Acceptance Criteria

1. **Judges Array Parsing:**
   - Given eval_config.json includes judges array
   - When the config is loaded
   - Then judges are parsed with deepeval name, threshold, custom criteria

2. **External Judge Config:**
   - Given a judge references a file in config/judges/
   - When the config is loaded
   - Then the file is loaded and merged with the judge config

3. **Invalid Judge Handling:**
   - Given a judge definition is invalid
   - When the config is loaded
   - Then a JudgeError is raised with guidance

## Tasks / Subtasks

- [x] Task 1: Create judge config models (AC: #1)
  - [x] Create JudgeConfig Pydantic model
  - [x] Create GEvalConfig model for custom judges
  - [x] Update EvalConfig to include judges array

- [x] Task 2: Implement config file loading (AC: #2)
  - [x] Add config_ref field to JudgeConfig
  - [x] Implement judge file loading from config/judges/
  - [x] Implement config merging logic
  - [x] Validate merged configs

- [x] Task 3: Add validation and error handling (AC: #3)
  - [x] Create JudgeError exception class
  - [x] Validate judge IDs are unique
  - [x] Validate deepeval_name is supported
  - [x] Validate threshold values (0.0-1.0)
  - [x] Add helpful error messages

- [x] Task 4: Write comprehensive tests
  - [x] Unit tests for judges array parsing
  - [x] Tests for all DeepEval judge types
  - [x] Tests for custom GEval configuration
  - [x] Tests for config_ref loading and merging
  - [x] Tests for duplicate judge IDs (JudgeError)
  - [x] Tests for invalid deepeval_name
  - [x] 17 comprehensive tests, all passing

## Dev Notes

### Judges Configuration Format

**In eval_config.json:**
```json
{
  "eval_name": "my_eval",
  "eval_type": "local",
  "judges": [
    {
      "name": "similarity",
      "type": "deepeval.similarity",
      "config": {
        "threshold": 0.8
      }
    },
    {
      "name": "custom_accuracy",
      "type": "deepeval.geval",
      "config_ref": "judges/custom_accuracy.json"
    }
  ]
}
```

**External Judge File (config/judges/custom_accuracy.json):**
```json
{
  "criteria": "Technical accuracy and clarity",
  "evaluation_steps": [
    "Check factual accuracy of technical claims",
    "Evaluate explanation clarity and completeness",
    "Verify code examples are correct"
  ],
  "model": "claude-3-5-sonnet-latest",
  "threshold": 0.7
}
```

### Supported DeepEval Judges

| Judge Type | deepeval_name | Config Parameters |
|------------|---------------|-------------------|
| Similarity | `deepeval.similarity` | threshold |
| Faithfulness | `deepeval.faithfulness` | threshold |
| Hallucination | `deepeval.hallucination` | threshold |
| Answer Relevancy | `deepeval.answer_relevancy` | threshold |
| Contextual Precision | `deepeval.contextual_precision` | threshold |
| Contextual Recall | `deepeval.contextual_recall` | threshold |
| Custom GEval | `deepeval.geval` | criteria, evaluation_steps, model |

### Pydantic Models

**JudgeConfig:**
```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, Optional

class JudgeConfig(BaseModel):
    """Judge configuration."""
    model_config = ConfigDict(extra='ignore')

    id: str = Field(..., description="Unique judge identifier")
    deepeval_name: str = Field(..., description="DeepEval judge type")
    config: Optional[Dict[str, Any]] = Field(None, description="Judge-specific config")
    config_ref: Optional[str] = Field(None, description="Path to external config file")
```

**GEvalConfig:**
```python
class GEvalConfig(BaseModel):
    """Custom GEval judge configuration."""
    model_config = ConfigDict(extra='ignore')

    criteria: str = Field(..., description="Evaluation criteria")
    evaluation_steps: list[str] = Field(..., description="Evaluation steps")
    model: str = Field(..., description="LLM model for evaluation")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Pass/fail threshold")
```

**Updated EvalConfig:**
```python
class EvalConfig(BaseModel):
    """Evaluation configuration."""
    model_config = ConfigDict(extra='ignore')

    eval_name: str
    eval_type: str
    processor_type: str
    scenarios_file: str
    agents_file: str
    judges_config: str
    output_dir: str
    judges: Optional[list[JudgeConfig]] = Field(None, description="Judge configurations")
```

### Config Loading and Merging

```python
from pathlib import Path
import json

def load_judge_config(
    judge: JudgeConfig,
    eval_root: Path,
) -> JudgeConfig:
    """Load judge config, merging external file if config_ref provided."""
    if not judge.config_ref:
        return judge

    # Load external config file
    config_file = eval_root / judge.config_ref
    if not config_file.exists():
        raise JudgeError(
            f"Judge config file not found: {judge.config_ref} - "
            f"Create file or fix config_ref path"
        )

    external_config = json.loads(config_file.read_text())

    # Merge configs (external overrides inline)
    merged_config = {**(judge.config or {}), **external_config}

    return JudgeConfig(
        name=judge.name,
        type=judge.type,
        config=merged_config,
        config_ref=judge.config_ref,
    )
```

### Judge Validation

**Unique Names:**
```python
def validate_judge_ids(judges: list[JudgeConfig]) -> None:
    """Validate judge names are unique."""
    judge_names = [j.name for j in judges]
    duplicates = [name for name in judge_names if judge_names.count(name) > 1]

    if duplicates:
        raise JudgeError(
            f"Duplicate judge names: {duplicates} - "
            f"Each judge must have unique name"
        )
```

**Supported Judge Names:**
```python
SUPPORTED_JUDGES = {
    "deepeval.similarity",
    "deepeval.faithfulness",
    "deepeval.hallucination",
    "deepeval.answer_relevancy",
    "deepeval.contextual_precision",
    "deepeval.contextual_recall",
    "deepeval.geval",
}

def validate_judge_type(judge: JudgeConfig) -> None:
    """Validate judge uses supported type."""
    if judge.type not in SUPPORTED_JUDGES:
        raise JudgeError(
            f"Unsupported judge type '{judge.type}' - "
            f"Use one of: {', '.join(SUPPORTED_JUDGES)}"
        )
```

**Threshold Validation:**
```python
def validate_threshold(threshold: float) -> None:
    """Validate threshold is between 0.0 and 1.0."""
    if not 0.0 <= threshold <= 1.0:
        raise ValidationError(
            f"Threshold {threshold} out of range - "
            f"Use value between 0.0 and 1.0"
        )
```

### GEval Configuration Validation

```python
def validate_geval_config(judge: JudgeConfig) -> None:
    """Validate GEval judge has required config."""
    if judge.type != "deepeval.geval":
        return

    if not judge.config:
        raise JudgeError(
            f"GEval judge '{judge.name}' missing config - "
            f"Add 'config' with criteria and evaluation_steps"
        )

    required = ["criteria", "evaluation_steps", "model"]
    missing = [f for f in required if f not in judge.config]

    if missing:
        raise JudgeError(
            f"GEval judge '{judge.name}' missing required fields: {missing} - "
            f"Add {', '.join(missing)} to config"
        )

    # Validate GEval config structure
    try:
        GEvalConfig.model_validate(judge.config)
    except ValidationError as e:
        raise JudgeError(
            f"Invalid GEval config for judge '{judge.name}' - "
            f"Fix validation errors: {e}"
        )
```

### Error Handling

**Exception Class:**
```python
from gavel_ai.core.exceptions import GavelError

class JudgeError(GavelError):
    """Judge configuration errors."""
    pass
```

**Error Messages:**
```python
# Missing judge file
raise JudgeError(
    f"Judge config file not found: {config_ref} - "
    f"Create file or fix config_ref path"
)

# Duplicate IDs
raise JudgeError(
    f"Duplicate judge IDs: {duplicates} - "
    f"Each judge must have unique ID"
)

# Unsupported judge
raise JudgeError(
    f"Unsupported judge '{deepeval_name}' - "
    f"Use one of: deepeval.similarity, deepeval.faithfulness, etc."
)

# Invalid threshold
raise ValidationError(
    f"Threshold {threshold} out of range - "
    f"Use value between 0.0 and 1.0"
)
```

### Testing Requirements

**Unit Tests** (`tests/unit/test_judge_config.py`):
- Parse judges array from eval_config.json
- Parse all DeepEval judge types
- Parse GEval custom configuration
- Validate threshold ranges
- Handle missing judge ID (JudgeError)
- Handle invalid deepeval_name (JudgeError)
- Validate config_ref loading
- Test config merging (inline + external)
- Validate judge ID uniqueness

**Integration Tests** (`tests/integration/test_judge_loading.py`):
- Load eval_config.json with judges array
- Load external judge configs from config/judges/
- Merge inline and external configs
- Validate complete judge configurations

**Test Coverage:** 70%+ on judge config logic

### Dependencies

**Blocked By:**
- Story 2.3 (Config Loading) - ✅ Must be complete

**Blocks:**
- Epic 4 (Judging) - All judge implementation stories need configs
- Story 4.1-4.5 (Judge Integration) - Use these configs

**External Dependencies:**
- `deepeval` - Judge library (will be integrated in Epic 4)

### File Structure

```
src/gavel_ai/
├── core/
│   └── config/
│       ├── judges.py         # JudgeConfig, GEvalConfig models
│       ├── eval_config.py    # Updated EvalConfig with judges
│       ├── models.py         # Updated with judge imports
│       └── errors.py         # JudgeError exception
```

### Functional Requirements Mapped

| FR | Requirement | Implementation |
|----|-------------|----------------|
| FR-1.5 | Judge customization | judges array with DeepEval and GEval |
| FR-4.1 | DeepEval integration | deepeval_name field with judge types |
| FR-4.2 | GEval configuration | GEvalConfig with criteria and steps |
| FR-4.5 | Configurable execution | Judge configs with thresholds |
| Decision 5 | DeepEval-native | deepeval.* namespace for judges |

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2-Story-6]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-5-Judge-Integration]
- [Source: _bmad-output/planning-artifacts/project-context.md#Judge-Configuration]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

N/A - Clean TDD implementation, all tests passing on first run

### Completion Notes

**Completed: 2025-12-28**

Implemented Story 2-6 using strict TDD red-green-refactor cycle:

**RED Phase:**
- Created 17 comprehensive tests in `tests/unit/test_judges_config.py`
- Test coverage: JudgeConfig model, GEvalConfig model, EvalConfig with judges array, external config loading/merging, validation functions

**GREEN Phase:**
- Moved JudgeConfig and GEvalConfig to `src/gavel_ai/core/config/models.py` (resolved circular import)
- Implemented validation functions in `src/gavel_ai/core/config/judges.py`:
  - `load_judge_config()`: Loads and merges external config files
  - `validate_judge_ids()`: Ensures unique judge IDs
  - `validate_deepeval_name()`: Validates supported judge types
- Added JudgeError to `src/gavel_ai/core/exceptions.py`
- Updated module exports in `src/gavel_ai/core/config/__init__.py`

**REFACTOR Phase:**
- All linting checks passed (ruff)
- Total tests: 136 passing (119 existing + 17 new)

**Implementation Details:**
- JudgeConfig and GEvalConfig use `ConfigDict(extra='ignore')` for forward compatibility
- EvalConfig.judges field typed as `Optional[List[JudgeConfig]]`
- Supported 7 DeepEval judge types: similarity, faithfulness, hallucination, answer_relevancy, contextual_precision, contextual_recall, geval
- Config merging: external config overrides inline config
- All error messages follow pattern: "<What> - <How to fix>"
- OpenTelemetry tracing on all judge operations

**Test Coverage:**
- 17 tests covering all acceptance criteria
- All DeepEval judge types tested
- External config file loading and merging tested
- Validation error cases tested (duplicate IDs, unsupported types, missing files)

### File List

- `src/gavel_ai/core/config/judges.py` (new) - Validation and loading functions
- `src/gavel_ai/core/config/models.py` (modified) - Added JudgeConfig, GEvalConfig, updated EvalConfig
- `src/gavel_ai/core/config/__init__.py` (modified) - Added exports
- `src/gavel_ai/core/exceptions.py` (modified) - Added JudgeError
- `tests/unit/test_judges_config.py` (new) - 17 comprehensive tests

## Change Log

- **2025-12-28:** Story created with comprehensive judge config implementation guide
- **2025-12-28:** Added DeepEval and GEval models, validation logic, config merging
