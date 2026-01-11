"""Scenario model definition."""

from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Scenario(BaseModel):
    """Test scenario definition."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

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
                import json

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
