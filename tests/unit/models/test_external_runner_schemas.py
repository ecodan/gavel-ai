"""
Unit tests for the external-runner JSON schemas (Tasks 52 and 53).

Task 52: Assert the schema generation script produces valid JSON Schema for all shapes.
Task 53: Round-trip check — construct a minimal ExternalTaskRequest, call model_dump(),
         and validate the dump against the published JSON Schema.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# jsonschema is a dev dependency; import at top level per project conventions
from jsonschema import Draft202012Validator, validate
from jsonschema.exceptions import SchemaError

from gavel_ai.models.runtime import ExternalJudgeRequest, ExternalTaskRequest, ExternalResponseEnvelope, ExternalIssue

REPO_ROOT: Path = Path(__file__).parent.parent.parent.parent
SCHEMAS_DIR: Path = REPO_ROOT / "docs" / "specs" / "schemas"

SCHEMA_FILES: list[str] = [
    "external_task_request.json",
    "external_judge_request.json",
    "external_response_envelope.json",
]


# ---------------------------------------------------------------------------
# Task 52: Schema-validity tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("schema_filename", SCHEMA_FILES)
def test_generated_schema_is_valid_json_schema(schema_filename: str) -> None:
    """Each generated schema file must be a valid JSON Schema (Draft 2020-12)."""
    schema_path: Path = SCHEMAS_DIR / schema_filename
    assert schema_path.exists(), (
        f"Schema file not found: {schema_path}. "
        "Run `uv run python scripts/generate_external_schemas.py` first."
    )
    schema: Dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    # check_schema raises SchemaError if the schema is invalid
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        pytest.fail(f"Schema {schema_filename} is not a valid JSON Schema: {exc}")


@pytest.mark.unit
def test_generation_script_exits_zero() -> None:
    """The schema generation script must complete successfully."""
    script_path: Path = REPO_ROOT / "scripts" / "generate_external_schemas.py"
    result: subprocess.CompletedProcess = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"generate_external_schemas.py exited {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


@pytest.mark.unit
def test_schemas_directory_contains_expected_files() -> None:
    """After generation, all expected schema files must be present."""
    for filename in SCHEMA_FILES:
        assert (SCHEMAS_DIR / filename).exists(), f"Missing schema file: {filename}"


@pytest.mark.unit
def test_task_request_schema_has_required_fr62_properties() -> None:
    """ExternalTaskRequest schema must include scenario data, custom config, prompt, trace_id per FR-6.2."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_task_request.json").read_text(encoding="utf-8")
    )
    properties: set[str] = set(schema.get("properties", {}).keys())
    required_fields: set[str] = {"scenario_id", "scenario_input", "rendered_prompt", "custom_config", "trace_id"}
    missing: set[str] = required_fields - properties
    assert not missing, f"ExternalTaskRequest schema missing FR-6.2 required fields: {missing}"


@pytest.mark.unit
def test_judge_request_schema_has_required_fr62_properties() -> None:
    """ExternalJudgeRequest schema must include scenario data, judge content, custom config, trace_id per FR-6.2."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_judge_request.json").read_text(encoding="utf-8")
    )
    properties: set[str] = set(schema.get("properties", {}).keys())
    required_fields: set[str] = {"scenario_id", "processor_output", "criteria", "custom_config", "trace_id"}
    missing: set[str] = required_fields - properties
    assert not missing, f"ExternalJudgeRequest schema missing FR-6.2 required fields: {missing}"


@pytest.mark.unit
def test_response_envelope_schema_has_required_fr63_properties() -> None:
    """ExternalResponseEnvelope schema must include status, result, metadata, issue per FR-6.3."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_response_envelope.json").read_text(encoding="utf-8")
    )
    properties: set[str] = set(schema.get("properties", {}).keys())
    required_fields: set[str] = {"status", "result", "metadata", "issue"}
    missing: set[str] = required_fields - properties
    assert not missing, f"ExternalResponseEnvelope schema missing FR-6.3 required fields: {missing}"


# ---------------------------------------------------------------------------
# Task 53: Round-trip check tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_external_task_request_round_trip_validates_against_schema() -> None:
    """A minimal ExternalTaskRequest instance must validate against its published schema."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_task_request.json").read_text(encoding="utf-8")
    )
    # Construct a minimal instance directly (no dependency on Partition 2/3 fixtures)
    request: ExternalTaskRequest = ExternalTaskRequest(
        scenario_id="test-scenario-001",
        scenario_input="What is 2 + 2?",
        rendered_prompt="You are a math assistant.\n\nUser: What is 2 + 2?\nAssistant:",
        custom_config={"model": "test-model"},
        trace_id="run-test-abc",
        metadata={"variant_id": "v1"},
    )
    dumped: Dict[str, Any] = request.model_dump()
    # Should not raise
    validate(instance=dumped, schema=schema)


@pytest.mark.unit
def test_external_task_request_minimal_required_only_validates() -> None:
    """A request with only required fields (no optionals) must also validate against the schema."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_task_request.json").read_text(encoding="utf-8")
    )
    request: ExternalTaskRequest = ExternalTaskRequest(
        scenario_id="s001",
        scenario_input="Hello",
        rendered_prompt="Hello world",
    )
    validate(instance=request.model_dump(), schema=schema)


@pytest.mark.unit
def test_external_task_request_dict_input_validates() -> None:
    """ExternalTaskRequest with dict scenario_input must validate against schema."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_task_request.json").read_text(encoding="utf-8")
    )
    request: ExternalTaskRequest = ExternalTaskRequest(
        scenario_id="s002",
        scenario_input={"question": "What is 2+2?", "context": "math"},
        rendered_prompt="Rendered prompt text",
    )
    validate(instance=request.model_dump(), schema=schema)


@pytest.mark.unit
def test_external_judge_request_round_trip_validates_against_schema() -> None:
    """A minimal ExternalJudgeRequest instance must validate against its published schema."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_judge_request.json").read_text(encoding="utf-8")
    )
    request: ExternalJudgeRequest = ExternalJudgeRequest(
        scenario_id="test-scenario-001",
        processor_output="The answer is 4.",
        criteria="Score 1-10 based on correctness of the math answer.",
        expected_behavior="A correct numerical answer",
        custom_config={"model": "gpt-4o"},
        trace_id="run-test-abc",
        metadata={},
    )
    validate(instance=request.model_dump(), schema=schema)


@pytest.mark.unit
def test_external_response_envelope_ok_validates_against_schema() -> None:
    """A success ExternalResponseEnvelope must validate against its published schema."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_response_envelope.json").read_text(encoding="utf-8")
    )
    envelope: ExternalResponseEnvelope = ExternalResponseEnvelope(
        status="ok",
        result={"output": "The answer is 4."},
        metadata={"timing_ms": 100},
        issue=None,
        trace_id="run-test-abc",
    )
    validate(instance=envelope.model_dump(), schema=schema)


@pytest.mark.unit
def test_external_response_envelope_with_issue_validates_against_schema() -> None:
    """An ExternalResponseEnvelope with an issue must validate against its published schema."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_response_envelope.json").read_text(encoding="utf-8")
    )
    envelope: ExternalResponseEnvelope = ExternalResponseEnvelope(
        status="ok",
        result={"output": "I think it might be 4."},
        metadata={},
        issue=ExternalIssue(code="low_confidence", level="warning", message="Confidence below threshold"),
        trace_id="run-test-abc",
    )
    validate(instance=envelope.model_dump(), schema=schema)


@pytest.mark.unit
def test_external_response_envelope_error_validates_against_schema() -> None:
    """An ExternalResponseEnvelope with status=error must validate against its published schema."""
    schema: Dict[str, Any] = json.loads(
        (SCHEMAS_DIR / "external_response_envelope.json").read_text(encoding="utf-8")
    )
    envelope: ExternalResponseEnvelope = ExternalResponseEnvelope(
        status="error",
        result=None,
        metadata={},
        issue=ExternalIssue(code="internal_error", level="error", message="Unhandled exception"),
    )
    validate(instance=envelope.model_dump(), schema=schema)
