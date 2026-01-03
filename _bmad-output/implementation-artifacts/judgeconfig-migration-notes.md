# JudgeConfig Field Name Migration

**Date:** 2026-01-03
**Story:** 4-4 (Judge Registry and Factory)

## Overview

JudgeConfig schema consolidated with standardized field names for clarity and framework-agnostic future expansion.

## Changes Made

### Field Names Updated

| Old Field | New Field | Purpose |
|-----------|-----------|---------|
| `id` | `name` | Judge identifier (e.g., "similarity", "custom_accuracy") |
| `deepeval_name` | `type` | Judge type (e.g., "deepeval.similarity", "custom.my_judge") |

### Function Names Updated

| Old Function | New Function | Purpose |
|--------------|--------------|---------|
| `validate_deepeval_name()` | `validate_judge_type()` | Validates judge type is supported |

### Example Changes

**Configuration File (eval_config.json):**

```json
// OLD
{"id": "similarity", "deepeval_name": "deepeval.similarity"}

// NEW
{"name": "similarity", "type": "deepeval.similarity"}
```

**Python Code:**

```python
# OLD
config = JudgeConfig(id="similarity", deepeval_name="deepeval.similarity")
judge_type = config.deepeval_name
validate_deepeval_name("deepeval.similarity")

# NEW
config = JudgeConfig(name="similarity", type="deepeval.similarity")
judge_type = config.type
validate_judge_type("deepeval.similarity")
```

## Rationale

1. **Clarity:** `name` is more intuitive than `id` (avoids confusion with database identifiers)
2. **Framework-Agnostic:** `type` prepares codebase for multi-framework support beyond DeepEval
3. **Consistency:** Single authoritative JudgeConfig schema across codebase
4. **Simplicity:** Removed compatibility properties (judge_id_value, judge_type_value)

## Breaking Changes

### Configuration Files

All eval_config.json files using `id` and `deepeval_name` must be updated:

```json
// BEFORE
{
  "judges": [
    {"id": "relevancy", "deepeval_name": "deepeval.answer_relevancy"}
  ]
}

// AFTER
{
  "judges": [
    {"name": "relevancy", "type": "deepeval.answer_relevancy"}
  ]
}
```

### Python Code

Any code accessing judge config fields must update:

```python
# BEFORE
if judge.config.deepeval_name in SUPPORTED_JUDGES:
    logger.info(f"Judge '{judge.config.id}' ready")

# AFTER
if judge.config.type in SUPPORTED_JUDGES:
    logger.info(f"Judge '{judge.config.name}' ready")
```

### Function Calls

Update validation function calls:

```python
# BEFORE
validate_deepeval_name(judge.deepeval_name)

# AFTER
validate_judge_type(judge.type)
```

## Files Modified

### Source Code

- `src/gavel_ai/core/config/models.py` - Unified JudgeConfig with `name` and `type` fields
- `src/gavel_ai/core/models.py` - Removed duplicate JudgeConfig, imported from core.config.models
- `src/gavel_ai/core/config/__init__.py` - Updated exports (validate_judge_type)
- `src/gavel_ai/core/config/judges.py` - Updated field access and function naming
- `src/gavel_ai/judges/judge_executor.py` - Updated all field references
- `src/gavel_ai/judges/deepeval_judge.py` - Updated field references (7 locations)
- `src/gavel_ai/judges/judge_registry.py` - Updated field reference

### Test Files

- `tests/unit/test_judges_config.py` - Updated fixtures and assertions
- `tests/unit/test_deepeval_judge.py` - Updated fixtures
- `tests/unit/test_judge_executor.py` - Updated JudgeConfig instantiations
- `tests/unit/test_judge_base.py` - Updated assertions for new field names
- `tests/unit/test_judge_registry.py` - Updated assertion
- `tests/unit/test_rejudge.py` - Updated JudgeConfig instantiations
- `tests/conftest.py` - Updated sample config fixture

### Documentation

- `_bmad-output/implementation-artifacts/2-6-implement-judge-configuration-schema.md` - Updated examples
- `_bmad-output/implementation-artifacts/4-4-implement-judge-registry-and-factory.md` - Updated code examples

## Testing

✅ All 78 unit tests passing
✅ All judge types covered (similarity, faithfulness, hallucination, answer_relevancy, geval)
✅ Configuration loading and merging validated
✅ Error handling verified

## Migration Path

1. **Configuration Files:** Update all eval_config.json files
   - Replace `"id"` keys with `"name"`
   - Replace `"deepeval_name"` keys with `"type"`

2. **Code:** Update any custom judge implementations or config access
   - Replace `config.id` with `config.name`
   - Replace `config.deepeval_name` with `config.type`
   - Update function calls: `validate_deepeval_name()` → `validate_judge_type()`

3. **External Systems:** If integrating with external tools that generate eval_config.json, update templates/generators

## Backward Compatibility

⚠️ **NO BACKWARD COMPATIBILITY**

This is a clean-break migration. Old field names are not supported in the new schema.

Attempting to use old field names will result in Pydantic validation errors:

```
ValidationError: 2 validation errors for JudgeConfig
name
  Field required [type=missing]
type
  Field required [type=missing]
```

## Questions?

Refer to Story 2-6 (Judge Configuration Schema) and Story 4-4 (Judge Registry) documentation for implementation details.
