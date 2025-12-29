# Story 2.5: Implement Scenarios Configuration

Status: review

## Story

As a user,
I want to define test scenarios in scenarios.json or scenarios.csv,
So that I can easily manage test cases and bulk import data.

## Acceptance Criteria

1. **JSON Scenarios:**
   - Given scenarios.json with array of scenarios
   - When the config is loaded
   - Then each scenario has: id, input (dict or key/value), expected_behavior (optional)

2. **CSV Scenarios:**
   - Given scenarios.csv with columns
   - When the config is loaded
   - Then columns are mapped to scenario input fields

3. **Placeholder Substitution:**
   - Given a scenario defines input with placeholders (e.g., {{user_input}})
   - When the evaluation runs
   - Then placeholders are substituted from scenario data

4. **Performance:**
   - Given 100+ scenarios
   - When they are loaded
   - Then performance is acceptable (<1s load time)

## Tasks / Subtasks

- [ ] Task 1: Create scenario models (AC: #1)
  - [ ] Create Scenario Pydantic model
  - [ ] Create ScenarioSet model for JSON format
  - [ ] Add validation for required fields (id, input)

- [ ] Task 2: Implement JSON loader (AC: #1)
  - [ ] Parse scenarios.json array format
  - [ ] Validate scenario structure
  - [ ] Handle optional expected_behavior field

- [ ] Task 3: Implement CSV loader (AC: #2)
  - [ ] Parse CSV with header row mapping
  - [ ] Convert CSV rows to Scenario objects
  - [ ] Handle various CSV formats and encodings

- [ ] Task 4: Implement placeholder system (AC: #3)
  - [ ] Create placeholder substitution logic
  - [ ] Support {{field_name}} syntax
  - [ ] Handle missing placeholders gracefully

- [ ] Task 5: Optimize performance (AC: #4)
  - [ ] Benchmark with 100+ scenarios
  - [ ] Optimize loading if needed
  - [ ] Add caching if beneficial

- [ ] Task 6: Write comprehensive tests
  - [ ] Unit tests for JSON parsing
  - [ ] Unit tests for CSV parsing
  - [ ] Tests for placeholder substitution
  - [ ] Performance tests (100+, 1000+ scenarios)
  - [ ] Tests for missing required fields
  - [ ] Edge case tests (special characters, encoding)

## Dev Notes

### Scenario Format (JSON)

**scenarios.json:**
```json
{
  "scenarios": [
    {
      "id": "scenario-1",
      "input": {
        "user_input": "What is the capital of France?",
        "context": "General knowledge"
      },
      "expected_behavior": "Accurate answer"
    },
    {
      "id": "scenario-2",
      "input": {
        "user_input": "Explain quantum computing in simple terms"
      },
      "expected_behavior": "",
      "metadata": {
        "category": "technology",
        "difficulty": "medium"
      }
    }
  ]
}
```

### Scenario Format (CSV)

**scenarios.csv:**
```csv
scenario_id,input,expected_output,category,difficulty
scenario-1,"What is the capital of France?","Paris",geography,easy
scenario-2,"Explain quantum computing in simple terms","",technology,medium
```

### Pydantic Models

**Scenario:**
```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, Optional

class Scenario(BaseModel):
    """Test scenario definition."""
    model_config = ConfigDict(extra='ignore')

    id: str = Field(..., description="Unique scenario identifier")
    input: Dict[str, Any] = Field(..., description="Scenario input data")
    expected_behavior: Optional[str] = Field(None, description="Expected output")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
```

**ScenarioSet:**
```python
class ScenarioSet(BaseModel):
    """Container for multiple scenarios."""
    model_config = ConfigDict(extra='ignore')

    scenarios: list[Scenario]
```

### JSON Loader Implementation

```python
from pathlib import Path
import json

def load_scenarios_json(file_path: Path) -> list[Scenario]:
    """Load scenarios from JSON file."""
    if not file_path.exists():
        raise ConfigError(
            f"Scenarios file not found: {file_path} - "
            f"Create scenarios.json or check path"
        )

    content = file_path.read_text()
    data = json.loads(content)

    try:
        scenario_set = ScenarioSet.model_validate(data)
        return scenario_set.scenarios
    except ValidationError as e:
        raise ValidationError(
            f"Invalid scenarios format in {file_path} - "
            f"Fix validation errors: {e}"
        )
```

### CSV Loader Implementation

```python
import csv
from typing import Dict, Any

def load_scenarios_csv(file_path: Path) -> list[Scenario]:
    """Load scenarios from CSV file."""
    if not file_path.exists():
        raise ConfigError(
            f"Scenarios file not found: {file_path} - "
            f"Create scenarios.csv or check path"
        )

    scenarios = []

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
            # Build scenario from CSV row
            scenario_id = row.get('scenario_id') or row.get('id')
            if not scenario_id:
                raise ValidationError(
                    f"Missing 'scenario_id' or 'id' in row {row_num} - "
                    f"Add scenario_id column to CSV"
                )

            # All other columns go into input dict
            input_data = {
                k: v for k, v in row.items()
                if k not in ('scenario_id', 'id', 'expected_behavior', 'expected_output')
            }

            expected = row.get('expected_behavior') or row.get('expected_output')

            scenario = Scenario(
                id=scenario_id,
                input=input_data,
                expected_behavior=expected
            )
            scenarios.append(scenario)

    return scenarios
```

### Placeholder Substitution

**Pattern:** `{{field_name}}` in input values

**Example:**
```json
{
  "id": "scenario-1",
  "input": {
    "prompt_template": "Translate '{{text}}' to French",
    "text": "Hello world"
  }
}
```

**Implementation:**
```python
import re
from typing import Any

def substitute_placeholders(
    template: str,
    data: Dict[str, Any],
) -> str:
    """Substitute {{field}} placeholders with data values."""
    pattern = r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"

    def replace(match):
        field_name = match.group(1)
        if field_name not in data:
            raise ValidationError(
                f"Placeholder '{{{{{field_name}}}}}' not found in scenario data - "
                f"Add '{field_name}' field or remove placeholder"
            )
        return str(data[field_name])

    return re.sub(pattern, replace, template)

def process_scenario_input(scenario: Scenario) -> Dict[str, Any]:
    """Process scenario input with placeholder substitution."""
    processed = {}

    for key, value in scenario.input.items():
        if isinstance(value, str) and "{{" in value:
            processed[key] = substitute_placeholders(value, scenario.input)
        else:
            processed[key] = value

    return processed
```

### Auto-Detection of Format

```python
def load_scenarios(file_path: Path) -> list[Scenario]:
    """Load scenarios from JSON or CSV based on file extension."""
    if file_path.suffix == ".json":
        return load_scenarios_json(file_path)
    elif file_path.suffix == ".csv":
        return load_scenarios_csv(file_path)
    else:
        raise ConfigError(
            f"Unsupported scenarios format: {file_path.suffix} - "
            f"Use .json or .csv"
        )
```

### Performance Optimization

**Requirements:**
- Load 100 scenarios in <100ms
- Load 1000 scenarios in <1s

**Strategies:**
1. **Streaming CSV parsing** for large files
2. **Lazy loading** if scenarios aren't all needed upfront
3. **Caching** parsed scenarios between runs

**Benchmark Test:**
```python
import time

def test_performance_100_scenarios():
    """Test loading performance with 100 scenarios."""
    scenarios = generate_test_scenarios(100)

    start = time.time()
    loaded = load_scenarios_json(scenarios_file)
    elapsed = time.time() - start

    assert elapsed < 0.1  # <100ms
    assert len(loaded) == 100

def test_performance_1000_scenarios():
    """Test loading performance with 1000 scenarios."""
    scenarios = generate_test_scenarios(1000)

    start = time.time()
    loaded = load_scenarios_json(scenarios_file)
    elapsed = time.time() - start

    assert elapsed < 1.0  # <1s
    assert len(loaded) == 1000
```

### Testing Requirements

**Unit Tests** (`tests/unit/test_scenarios_config.py`):
- Load scenarios.json with valid data
- Load scenarios.csv with various formats
- Handle missing required fields (id, input)
- Handle optional fields (expected_behavior, metadata)
- Validate placeholder substitution
- Handle missing placeholder references
- Test special characters in input data
- Test CSV encoding (UTF-8, etc.)

**Performance Tests** (`tests/performance/test_scenarios_loading.py`):
- Benchmark 100 scenarios (<100ms)
- Benchmark 1000 scenarios (<1s)
- Memory usage with large scenario sets

**Integration Tests** (`tests/integration/test_scenarios_execution.py`):
- Load scenarios → process with placeholder substitution
- Use scenarios in evaluation workflow

**Test Coverage:** 70%+ on scenario loading logic

### Dependencies

**Blocked By:**
- Story 2.3 (Config Loading) - ✅ Must be complete

**Blocks:**
- Epic 3 (Execution) - Needs scenarios to run
- Story 3.1-3.4 (Processors) - Use scenario data

**External Dependencies:**
- `csv` (built-in) - CSV parsing
- `re` (built-in) - Placeholder pattern matching

### File Structure

```
src/gavel_ai/
├── core/
│   └── config/
│       ├── scenarios.py      # Scenario, ScenarioSet models + loaders
│       └── models.py         # Updated with scenario imports
├── data/
│   ├── __init__.py
│   └── placeholder.py        # Placeholder substitution logic
```

### Functional Requirements Mapped

| FR | Requirement | Implementation |
|----|-------------|----------------|
| FR-1.4 | Test scenarios | scenarios.json/csv with structured data |
| FR-1.6 | Templating | {{field}} placeholder substitution |

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2-Story-5]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-2-Code-Standards]
- [Source: _bmad-output/planning-artifacts/project-context.md#Scenario-Format]

## Dev Agent Record

### Agent Model Used

(To be filled by dev agent)

### Debug Log References

(To be filled by dev agent)

### Completion Notes

(To be filled by dev agent)

### File List

- `src/gavel_ai/core/config/scenarios.py` (new)
- `src/gavel_ai/core/config/models.py` (modified)
- `src/gavel_ai/data/__init__.py` (new)
- `src/gavel_ai/data/placeholder.py` (new)
- `tests/unit/test_scenarios_config.py` (new)
- `tests/performance/test_scenarios_loading.py` (new)
- `tests/integration/test_scenarios_execution.py` (new)

## Change Log

- **2025-12-28:** Story created with comprehensive scenarios config implementation guide
- **2025-12-28:** Added JSON/CSV loaders, placeholder substitution, performance requirements
