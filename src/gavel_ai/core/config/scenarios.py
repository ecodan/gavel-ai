"""Scenarios configuration schema with JSON and CSV loaders."""

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic import ValidationError as PydanticValidationError

from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)


class Scenario(BaseModel):
    """Test scenario definition."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)  # Forward compatible

    scenario_id: str = Field(..., validation_alias="id", description="Unique scenario identifier")
    input: Union[str, Dict[str, Any]] = Field(
        ..., description="Scenario input (prompt/question or dict)"
    )
    expected: Optional[str] = Field(
        None, validation_alias="expected_behavior", description="Expected output"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("input", mode="before")
    @classmethod
    def convert_input_to_string(cls, v: Any) -> str:
        """Convert dict input to string for backward compatibility."""
        if isinstance(v, dict):
            # Legacy format: convert dict to string representation
            # Typically has "user_input" or similar key
            if "user_input" in v:
                return v["user_input"]
            elif "input" in v:
                return v["input"]
            elif "prompt" in v:
                return v["prompt"]
            else:
                # Convert dict to JSON string as fallback
                return json.dumps(v)
        return str(v)

    @property
    def id(self) -> str:
        """Backward compatibility: access scenario_id as id."""
        return self.scenario_id

    @property
    def expected_behavior(self) -> Optional[str]:
        """Backward compatibility: access expected as expected_behavior."""
        return self.expected


class ScenarioSet(BaseModel):
    """Container for multiple scenarios."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    scenarios: List[Scenario]


def load_scenarios_json(file_path: Path) -> List[Scenario]:
    """Load scenarios from JSON file.

    Supports both formats:
    - Root-level array: [{ scenario_id, input, expected, metadata }, ...]
    - Wrapped object: { scenarios: [{ id, input, expected_behavior }, ...] }

    Args:
        file_path: Path to scenarios.json file

    Returns:
        List of parsed Scenario objects

    Raises:
        ConfigError: If file not found or invalid JSON
        ValidationError: If scenarios don't match schema
    """
    span.set_attribute("file_path", str(file_path))

    if not file_path.exists():
        raise ConfigError(
            f"Scenarios file not found: {file_path} - Create scenarios.json or check path"
        )

    content = file_path.read_text()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {file_path} - Fix JSON syntax: {e}") from None

    try:
        # Handle both formats:
        # 1. Root-level array: [{ scenario_id, input, expected, ... }, ...]
        # 2. Wrapped object: { scenarios: [...] }
        if isinstance(data, list):
            # Root-level array format (new)
            scenarios = [Scenario.model_validate(item) for item in data]
            return scenarios
        else:
            # Wrapped object format (legacy)
            scenario_set = ScenarioSet.model_validate(data)
            return scenario_set.scenarios
    except PydanticValidationError as e:
        raise ValidationError(
            f"Invalid scenarios format in {file_path} - Fix validation errors: {e}"
        ) from None


def load_scenarios_csv(file_path: Path) -> List[Scenario]:
    """Load scenarios from CSV file.

    CSV format:
    - scenario_id: Unique identifier
    - input: Scenario input/prompt
    - expected: Expected output (optional)
    - metadata: Additional metadata (optional)

    Args:
        file_path: Path to scenarios.csv file

    Returns:
        List of parsed Scenario objects

    Raises:
        ConfigError: If file not found
        ValidationError: If CSV missing required columns
    """
    span.set_attribute("file_path", str(file_path))

    if not file_path.exists():
        raise ConfigError(
            f"Scenarios file not found: {file_path} - Create scenarios.csv or check path"
        )

    scenarios: List[Scenario] = []

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):  # Header is row 1
            # Get scenario ID from either 'scenario_id' or 'id' (legacy) column
            scenario_id = row.get("scenario_id") or row.get("id")
            if not scenario_id:
                raise ValidationError(
                    f"Missing 'scenario_id' in row {row_num} - Add scenario_id column to CSV"
                )

            # Get input/prompt
            input_text = row.get("input")
            if not input_text:
                raise ValidationError(f"Missing 'input' in row {row_num} - Add input column to CSV")

            # Get expected output from either column name
            expected = row.get("expected") or row.get("expected_behavior")

            scenario = Scenario(
                scenario_id=scenario_id,
                input=input_text,
                expected=expected,
                metadata=None,
            )
            scenarios.append(scenario)

    return scenarios


def load_scenarios(file_path: Path) -> List[Scenario]:
    """Load scenarios from JSON or CSV based on file extension.

    Args:
        file_path: Path to scenarios file (.json or .csv)

    Returns:
        List of parsed Scenario objects

    Raises:
        ConfigError: If format unsupported or file not found
    """
    span.set_attribute("file_path", str(file_path))

    if file_path.suffix == ".json":
        return load_scenarios_json(file_path)
    elif file_path.suffix == ".csv":
        return load_scenarios_csv(file_path)
    else:
        raise ConfigError(f"Unsupported scenarios format: {file_path.suffix} - Use .json or .csv")


def substitute_placeholders(template: str, data: Dict[str, Any]) -> str:
    """Substitute {{field}} placeholders with data values.

    Args:
        template: String with {{field_name}} placeholders
        data: Dictionary with field values

    Returns:
        String with placeholders replaced

    Raises:
        ValidationError: If placeholder field not found in data
    """
    pattern = r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"

    def replace(match: re.Match[str]) -> str:
        field_name = match.group(1)
        if field_name not in data:
            raise ValidationError(
                f"Placeholder '{{{{{field_name}}}}}' not found in scenario data - "
                f"Add '{field_name}' field or remove placeholder"
            )
        return str(data[field_name])

    return re.sub(pattern, replace, template)


def process_scenario_input(scenario: Scenario) -> str:
    """Process scenario input with placeholder substitution.

    Args:
        scenario: Scenario with potentially placeholder-containing input

    Returns:
        Processed input string with placeholders substituted
    """
    if "{{" not in scenario.input:
        return scenario.input

    # Build substitution context from scenario metadata and fields
    context: Dict[str, Any] = {}
    if scenario.metadata:
        context.update(scenario.metadata)
    context["input"] = scenario.input
    if scenario.expected:
        context["expected"] = scenario.expected

    return substitute_placeholders(scenario.input, context)
