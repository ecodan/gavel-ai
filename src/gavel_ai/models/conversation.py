"""
Conversational scenario models for multi-turn evaluation.

This module provides Pydantic models for conversational scenarios that support
multi-turn dialogue evaluation with user goals, context, and dialogue guidance.

Models:
- DialogueGuidance: Guidance for turn generation behavior
- ConversationScenario: Conversational scenario definition with user_goal
- TurnMetadata: Metadata for a single conversation turn (tokens, latency)
- Turn: A single turn in a conversation
- ConversationState: State of a multi-turn conversation

Utilities:
- load_conversation_scenarios: Load scenarios from JSON/JSONL file
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field, field_validator


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


class TurnMetadata(BaseModel):
    """Metadata for a single conversation turn.

    Contains optional metrics about the turn such as token counts and latency.
    """

    model_config = ConfigDict(extra="ignore")

    tokens_prompt: Optional[int] = Field(
        None,
        description="Number of prompt tokens for this turn",
    )
    tokens_completion: Optional[int] = Field(
        None,
        description="Number of completion tokens for this turn",
    )
    latency_ms: Optional[int] = Field(
        None,
        description="Latency in milliseconds for this turn",
    )
    extra: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for extensibility",
    )


class Turn(BaseModel):
    """A single turn in a conversation.

    Represents one message in the dialogue, either from user or assistant.
    """

    model_config = ConfigDict(extra="ignore")

    turn_number: int = Field(
        ...,
        ge=0,
        description="Zero-indexed turn number",
    )
    role: Literal["user", "assistant"] = Field(
        ...,
        description="Role of the speaker: user or assistant",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Content of the turn",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when turn was created",
    )
    metadata: Optional[TurnMetadata] = Field(
        None,
        description="Optional metadata (tokens, latency)",
    )


class ConversationState(BaseModel):
    """State of a multi-turn conversation.

    Tracks the full dialogue history and provides methods for adding turns
    and accessing the conversation history.
    """

    model_config = ConfigDict(extra="ignore")

    scenario_id: str = Field(
        ...,
        description="ID of the scenario being executed",
    )
    variant_id: str = Field(
        ...,
        description="ID of the variant (model/config) being tested",
    )
    turns: List[Turn] = Field(
        default_factory=list,
        description="List of conversation turns",
    )
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when conversation started",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional conversation metadata",
    )

    def add_turn(
        self,
        role: Literal["user", "assistant"],
        content: str,
        metadata: Optional[TurnMetadata] = None,
    ) -> Turn:
        """Add a new turn to the conversation.

        Args:
            role: Speaker role ("user" or "assistant")
            content: Turn content
            metadata: Optional turn metadata

        Returns:
            The created Turn object
        """
        turn = Turn(
            turn_number=len(self.turns),
            role=role,
            content=content,
            metadata=metadata,
        )
        self.turns.append(turn)
        return turn

    @property
    def history(self) -> str:
        """Get formatted conversation history.

        Returns:
            String formatted as "user: content\\nassistant: content\\n..."
            Empty string if no turns.
        """
        if not self.turns:
            return ""
        return "\n".join(f"{turn.role}: {turn.content}" for turn in self.turns)


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


class TurnResult(BaseModel):
    """Result of processing a single conversation turn.

    Supports partial updates and ignoring extra fields for robust parsing.
    """
    model_config = ConfigDict(extra='ignore')

    turn_number: int = Field(
        ...,
        ge=0,
        description="Turn number this result corresponds to"
    )
    processor_output: str = Field(
        ...,
        description="Assistant response (processor output)"
    )
    latency_ms: int = Field(
        ...,
        ge=0,
        description="Processing time in milliseconds"
    )
    tokens_prompt: Optional[int] = Field(
        None,
        description="Number of prompt tokens"
    )
    tokens_completion: Optional[int] = Field(
        None,
        description="Number of completion tokens"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if turn processing failed"
    )


class ConversationResult(BaseModel):
    """Complete result of a conversational evaluation execution."""
    model_config = ConfigDict(extra='ignore')

    scenario_id: str = Field(
        ...,
        description="ID of the scenario that was executed"
    )
    variant_id: str = Field(
        ...,
        description="ID of the variant (model/config) used"
    )
    conversation_transcript: ConversationState = Field(
        ...,
        description="Full conversation transcript with all turns"
    )
    results_raw: List[TurnResult] = Field(
        default_factory=list,
        description="Per-turn processor results"
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Total conversation duration in milliseconds"
    )
    tokens_total: int = Field(
        0,
        ge=0,
        description="Total tokens used across all turns"
    )
    completed: bool = Field(
        False,
        description="Whether conversation completed successfully (goal achieved or max_turns). False does not strictly imply error."
    )
    error: Optional[str] = Field(
        None,
        description="Conversation-level error if execution failed"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this result was created"
    )

    @computed_field
    @property
    def total_turns(self) -> int:
        """Total number of turns in the conversation."""
        return len(self.conversation_transcript.turns)

    @field_validator("tokens_total")
    @classmethod
    def validate_tokens_total(cls, v: int, info: Any) -> int:
        """Validate consistency if results_raw is present, but allow override."""
        # Note: We prioritize the explicitly set value, but could warn or enforce here.
        # For now, we just ensure it's non-negative (already covered by ge=0).
        return v

    def compute_tokens_total(self) -> int:
        """Compute total tokens from all turn results."""
        total = 0
        for result in self.results_raw:
            if result.tokens_prompt:
                total += result.tokens_prompt
            if result.tokens_completion:
                total += result.tokens_completion
        return total

    def to_jsonl_entry(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for JSONL serialization.

        Returns:
            Dict ready for json.dumps() with ISO format datetimes.
            Excludes None values to optimize storage.
        """
        return self.model_dump(
            mode='json',
            exclude_none=True,
        )
