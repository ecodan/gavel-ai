"""
Conversational scenario models for multi-turn evaluation.

This module provides Pydantic models for conversational scenarios that support
multi-turn dialogue evaluation with user goals, context, and dialogue guidance.

Models:
- DialogueGuidance: Guidance for turn generation behavior
- ConversationScenario: Conversational scenario definition with user_goal

Utilities:
- load_conversation_scenarios: Load scenarios from JSON/JSONL file
"""

import json
from pathlib import Path
from typing import Any, Iterator, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class DialogueGuidance(BaseModel):
    """Guidance for turn generation behavior.

    Provides hints to the turn generator about how the simulated user
    should behave during the conversation.
    """

    model_config = ConfigDict(extra="ignore")

    tone_preference: Optional[str] = Field(
        None,
        description="Desired tone: professional, casual, frustrated, confused, etc.",
    )
    escalation_strategy: Optional[str] = Field(
        None,
        description="How user should escalate if goal not met: politely insist, express frustration, ask for supervisor, etc.",
    )
    factual_constraints: Optional[List[str]] = Field(
        None,
        description="Facts the simulated user knows and may reference",
    )


class ConversationScenario(BaseModel):
    """Conversational scenario for multi-turn evaluation.

    Defines a scenario with a user goal that the simulated user is trying
    to accomplish through multi-turn conversation.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    scenario_id: str = Field(
        ...,
        validation_alias="id",
        description="Unique scenario identifier",
    )
    user_goal: str = Field(
        ...,
        description="Clear, actionable description of what the simulated user is trying to accomplish",
    )
    context: Optional[str] = Field(
        None,
        description="Background context for the conversation",
    )
    dialogue_guidance: Optional[DialogueGuidance] = Field(
        None,
        description="Guidance for turn generation behavior",
    )

    @field_validator("user_goal", mode="before")
    @classmethod
    def validate_user_goal(cls, v: Any) -> str:
        """Validate that user_goal is not empty.

        Raises:
            ValueError: If user_goal is empty or whitespace only.
        """
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(
                "user_goal cannot be empty - Provide a clear description of what the simulated user is trying to accomplish"
            )
        return v

    @property
    def id(self) -> str:
        """Backward compatibility: access scenario_id as id."""
        return self.scenario_id


def load_conversation_scenarios(
    path: Union[str, Path],
) -> List[ConversationScenario]:
    """
    Load conversational scenarios from a JSON or JSONL file.

    Args:
        path: Path to scenarios file (.json or .jsonl)

    Returns:
        List of ConversationScenario objects

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file format is not supported or data is invalid
        ValidationError: If scenario validation fails (e.g., missing user_goal)

    Example:
        >>> scenarios = load_conversation_scenarios("data/scenarios.json")
        >>> for scenario in scenarios:
        ...     print(f"{scenario.id}: {scenario.user_goal}")
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Scenario file not found: {path} - Check file path and ensure it exists"
        )

    content = path.read_text(encoding="utf-8")
    ext = path.suffix.lower()

    scenarios: List[ConversationScenario] = []
    raw_records: List[dict] = []

    if ext == ".json":
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError(
                f"JSON file must contain an array of scenarios - Got {type(data).__name__}"
            )
        raw_records = data

    elif ext == ".jsonl":
        for line_num, line in enumerate(content.splitlines(), start=1):
            if line.strip():
                try:
                    raw_records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON on line {line_num} - {e}") from e
    else:
        raise ValueError(f"Unsupported file format: {ext} - Use .json or .jsonl")

    for idx, record in enumerate(raw_records):
        try:
            scenarios.append(ConversationScenario(**record))
        except ValidationError as e:
            scenario_id = record.get("id", record.get("scenario_id", f"index {idx}"))
            raise ValueError(
                f"ConversationScenario validation failed for '{scenario_id}' - {e.errors()[0]['msg']}"
            ) from e

    return scenarios


def iter_conversation_scenarios(
    path: Union[str, Path],
) -> Iterator[ConversationScenario]:
    """
    Stream conversational scenarios from a file (memory efficient).

    Args:
        path: Path to scenarios file (.json or .jsonl)

    Yields:
        ConversationScenario objects one at a time

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file format is not supported or data is invalid
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Scenario file not found: {path} - Check file path and ensure it exists"
        )

    ext = path.suffix.lower()

    if ext == ".jsonl":
        with path.open(encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                if line.strip():
                    try:
                        record = json.loads(line)
                        yield ConversationScenario(**record)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON on line {line_num} - {e}") from e
                    except ValidationError as e:
                        scenario_id = record.get(
                            "id", record.get("scenario_id", f"line {line_num}")
                        )
                        raise ValueError(
                            f"ConversationScenario validation failed for '{scenario_id}' - {e.errors()[0]['msg']}"
                        ) from e
    else:
        # For JSON files, load all at once (can't stream)
        yield from load_conversation_scenarios(path)
