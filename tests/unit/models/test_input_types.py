"""
Unit tests for Input subclass types.

Tests creation, validation, and field handling for:
- PromptInput
- RemoteSystemInput
- ConversationalInput
"""

import pytest

from gavel_ai.models.runtime import (
    ConversationalInput,
    PromptInput,
    RemoteSystemInput,
)


class TestPromptInput:
    """Test PromptInput creation and validation."""

    def test_create_with_user_only(self) -> None:
        """Create PromptInput with user prompt only."""
        input_item = PromptInput(
            id="test-001",
            user="Extract headlines from the HTML: <html>...",
        )
        assert input_item.id == "test-001"
        assert input_item.user == "Extract headlines from the HTML: <html>..."
        assert input_item.system is None
        assert input_item.metadata == {}

    def test_create_with_user_and_system(self) -> None:
        """Create PromptInput with both user and system prompts."""
        input_item = PromptInput(
            id="test-002",
            user="Extract headlines from the HTML",
            system="You are a news content analyzer. Return only JSON.",
        )
        assert input_item.id == "test-002"
        assert input_item.user == "Extract headlines from the HTML"
        assert input_item.system == "You are a news content analyzer. Return only JSON."

    def test_create_with_metadata(self) -> None:
        """Create PromptInput with metadata."""
        metadata = {
            "scenario_input": {"site": "www.bbc.com", "html": "<html>..."},
            "template": "default:v1",
        }
        input_item = PromptInput(
            id="test-003",
            user="Process this content",
            metadata=metadata,
        )
        assert input_item.metadata == metadata
        assert input_item.metadata["template"] == "default:v1"

    def test_user_is_required(self) -> None:
        """Test that user field is required."""
        with pytest.raises(ValueError):
            PromptInput(id="test-004")  # type: ignore

    def test_id_is_required(self) -> None:
        """Test that id field is required."""
        with pytest.raises(ValueError):
            PromptInput(user="Test prompt")  # type: ignore


class TestRemoteSystemInput:
    """Test RemoteSystemInput creation and validation."""

    def test_create_basic(self) -> None:
        """Create RemoteSystemInput with required fields."""
        input_item = RemoteSystemInput(
            id="api-001",
            endpoint="https://api.example.com/analyze",
            method="POST",
            headers={"Content-Type": "application/json"},
            body={"text": "sample content"},
        )
        assert input_item.id == "api-001"
        assert input_item.endpoint == "https://api.example.com/analyze"
        assert input_item.method == "POST"
        assert input_item.headers == {"Content-Type": "application/json"}
        assert input_item.body == {"text": "sample content"}
        assert input_item.auth is None

    def test_create_with_auth(self) -> None:
        """Create RemoteSystemInput with authentication."""
        input_item = RemoteSystemInput(
            id="api-002",
            endpoint="https://api.example.com/v1/models/evaluate",
            method="POST",
            headers={"Content-Type": "application/json"},
            body={"data": "test"},
            auth={"bearer_token": "sk-12345"},
        )
        assert input_item.auth == {"bearer_token": "sk-12345"}

    def test_headers_default_empty(self) -> None:
        """Test that headers default to empty dict."""
        input_item = RemoteSystemInput(
            id="api-003",
            endpoint="https://api.example.com/",
            method="GET",
            body={},
        )
        assert input_item.headers == {}

    def test_body_default_empty(self) -> None:
        """Test that body defaults to empty dict."""
        input_item = RemoteSystemInput(
            id="api-004",
            endpoint="https://api.example.com/status",
            method="GET",
        )
        assert input_item.body == {}

    def test_endpoint_is_required(self) -> None:
        """Test that endpoint field is required."""
        with pytest.raises(ValueError):
            RemoteSystemInput(  # type: ignore
                id="api-005",
                method="POST",
                headers={},
                body={},
            )

    def test_method_is_required(self) -> None:
        """Test that method field is required."""
        with pytest.raises(ValueError):
            RemoteSystemInput(  # type: ignore
                id="api-006",
                endpoint="https://api.example.com/",
                headers={},
                body={},
            )


class TestConversationalInput:
    """Test ConversationalInput creation and validation."""

    def test_create_basic(self) -> None:
        """Create ConversationalInput with turns."""
        turns = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "The answer is 4."},
            {"role": "user", "content": "Explain how."},
        ]
        input_item = ConversationalInput(
            id="conv-001",
            turns=turns,
        )
        assert input_item.id == "conv-001"
        assert input_item.turns == turns
        assert input_item.system is None

    def test_create_with_system(self) -> None:
        """Create ConversationalInput with system instructions."""
        turns = [{"role": "user", "content": "Hello"}]
        input_item = ConversationalInput(
            id="conv-002",
            turns=turns,
            system="You are a helpful math tutor.",
        )
        assert input_item.system == "You are a helpful math tutor."
        assert len(input_item.turns) == 1

    def test_create_with_metadata(self) -> None:
        """Create ConversationalInput with metadata."""
        turns = [{"role": "user", "content": "test"}]
        metadata = {"conversation_id": "c-123"}
        input_item = ConversationalInput(
            id="conv-003",
            turns=turns,
            metadata=metadata,
        )
        assert input_item.metadata == metadata

    def test_turns_is_required(self) -> None:
        """Test that turns field is required."""
        with pytest.raises(ValueError):
            ConversationalInput(id="conv-004")  # type: ignore

    def test_empty_turns_list(self) -> None:
        """Test that empty turns list is allowed."""
        input_item = ConversationalInput(id="conv-005", turns=[])
        assert input_item.turns == []


class TestInputBase:
    """Test base Input class inheritance."""

    def test_metadata_default_empty_dict(self) -> None:
        """Test that metadata defaults to empty dict for all subclasses."""
        prompt = PromptInput(id="p-1", user="test")
        remote = RemoteSystemInput(
            id="r-1", endpoint="https://example.com", method="GET", body={}
        )
        conv = ConversationalInput(id="c-1", turns=[])

        assert prompt.metadata == {}
        assert remote.metadata == {}
        assert conv.metadata == {}

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored (extra='ignore' config)."""
        # This should not raise an error
        input_item = PromptInput(
            id="p-2",
            user="test",
            extra_field="should be ignored",  # type: ignore
        )
        assert input_item.id == "p-2"
        assert not hasattr(input_item, "extra_field")


@pytest.mark.unit
class TestInputTypeContracts:
    """Test type contracts and field requirements."""

    def test_prompt_input_json_serialization(self) -> None:
        """Test PromptInput can be serialized to JSON."""
        input_item = PromptInput(
            id="p-3",
            user="Test prompt",
            system="Test system",
            metadata={"key": "value"},
        )
        json_dict = input_item.model_dump(exclude_none=False)
        assert json_dict["id"] == "p-3"
        assert json_dict["user"] == "Test prompt"
        assert json_dict["system"] == "Test system"

    def test_remote_input_json_serialization(self) -> None:
        """Test RemoteSystemInput can be serialized to JSON."""
        input_item = RemoteSystemInput(
            id="r-2",
            endpoint="https://api.example.com",
            method="POST",
            headers={"X-Custom": "header"},
            body={"data": "value"},
        )
        json_dict = input_item.model_dump(exclude_none=True)
        assert json_dict["endpoint"] == "https://api.example.com"
        assert "auth" not in json_dict  # Excluded because it's None

    def test_conversational_input_json_serialization(self) -> None:
        """Test ConversationalInput can be serialized to JSON."""
        input_item = ConversationalInput(
            id="c-2",
            turns=[{"role": "user", "content": "Hello"}],
            system="You are helpful",
        )
        json_dict = input_item.model_dump()
        assert len(json_dict["turns"]) == 1
        assert json_dict["system"] == "You are helpful"
