"""Scenarios configuration schema with JSON and CSV loaders."""
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)


class Scenario(BaseModel):
    """Test scenario definition."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    id: str = Field(..., description="Unique scenario identifier")
    input: Dict[str, Any] = Field(..., description="Scenario input data")
    expected_behavior: Optional[str] = Field(None, description="Expected output")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ScenarioSet(BaseModel):
    """Container for multiple scenarios."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    scenarios: List[Scenario]


def load_scenarios_json(file_path: Path) -> List[Scenario]:
    """Load scenarios from JSON file.

    Args:
        file_path: Path to scenarios.json file

    Returns:
        List of parsed Scenario objects

    Raises:
        ConfigError: If file not found or invalid JSON
        ValidationError: If scenarios don't match schema
    """
    with tracer.start_as_current_span("scenarios.load_scenarios_json") as span:
        span.set_attribute("file_path", str(file_path))

        if not file_path.exists():
            raise ConfigError(
                f"Scenarios file not found: {file_path} - "
                f"Create scenarios.json or check path"
            )

        content = file_path.read_text()

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Invalid JSON in {file_path} - Fix JSON syntax: {e}"
            ) from None

        try:
            scenario_set = ScenarioSet.model_validate(data)
            return scenario_set.scenarios
        except PydanticValidationError as e:
            raise ValidationError(
                f"Invalid scenarios format in {file_path} - Fix validation errors: {e}"
            ) from None


def load_scenarios_csv(file_path: Path) -> List[Scenario]:
    """Load scenarios from CSV file.

    Args:
        file_path: Path to scenarios.csv file

    Returns:
        List of parsed Scenario objects

    Raises:
        ConfigError: If file not found
        ValidationError: If CSV missing required columns
    """
    with tracer.start_as_current_span("scenarios.load_scenarios_csv") as span:
        span.set_attribute("file_path", str(file_path))

        if not file_path.exists():
            raise ConfigError(
                f"Scenarios file not found: {file_path} - "
                f"Create scenarios.csv or check path"
            )

        scenarios: List[Scenario] = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # Header is row 1
                # Get scenario ID from either 'scenario_id' or 'id' column
                scenario_id = row.get("scenario_id") or row.get("id")
                if not scenario_id:
                    raise ValidationError(
                        f"Missing 'scenario_id' or 'id' in row {row_num} - "
                        f"Add scenario_id column to CSV"
                    )

                # All other columns go into input dict (except special columns)
                excluded_cols = {
                    "scenario_id",
                    "id",
                    "expected_behavior",
                    "expected_output",
                }
                input_data = {k: v for k, v in row.items() if k not in excluded_cols}

                # Get expected output from either column name
                expected = row.get("expected_behavior") or row.get("expected_output")

                scenario = Scenario(
                    id=scenario_id, input=input_data, expected_behavior=expected
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
    with tracer.start_as_current_span("scenarios.load_scenarios") as span:
        span.set_attribute("file_path", str(file_path))

        if file_path.suffix == ".json":
            return load_scenarios_json(file_path)
        elif file_path.suffix == ".csv":
            return load_scenarios_csv(file_path)
        else:
            raise ConfigError(
                f"Unsupported scenarios format: {file_path.suffix} - Use .json or .csv"
            )


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


def process_scenario_input(scenario: Scenario) -> Dict[str, Any]:
    """Process scenario input with placeholder substitution.

    Args:
        scenario: Scenario with potentially placeholder-containing input

    Returns:
        Processed input dictionary with placeholders substituted
    """
    with tracer.start_as_current_span("scenarios.process_scenario_input"):
        processed: Dict[str, Any] = {}

        for key, value in scenario.input.items():
            if isinstance(value, str) and "{{" in value:
                processed[key] = substitute_placeholders(value, scenario.input)
            else:
                processed[key] = value

        return processed
