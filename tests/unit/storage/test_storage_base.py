"""
Tests for storage base classes (Run, Config, Prompt ABCs).

Validates abstract interfaces and ensures concrete implementations
must implement all abstract methods.
"""

from typing import Any, Dict

import pytest

from gavel_ai.core.models import ArtifactRef
from gavel_ai.storage.base import Config, Prompt, Run


class ConcreteTestRun(Run):
    """Concrete Run implementation for testing."""

    async def save(self) -> str:
        return "test-path"

    @staticmethod
    async def load(run_id: str, storage_path: str = ".gavel") -> "Run":
        return ConcreteTestRun(run_id, {})

    @property
    def artifacts(self) -> Dict[str, ArtifactRef]:
        return {}


class ConcreteTestConfig(Config):
    """Concrete Config implementation for testing."""

    async def load(self) -> Dict[str, Any]:
        return {"test": "data"}

    async def save(self, config_data: Dict[str, Any]) -> None:
        pass


class ConcreteTestPrompt(Prompt):
    """Concrete Prompt implementation for testing."""

    async def load(self, version: str = "latest") -> str:
        return "test prompt content"

    async def save(self, version: str, content: str) -> None:
        pass


# Run ABC Tests


def test_run_instantiation():
    """Run can be instantiated with run_id and metadata."""
    run = ConcreteTestRun("test-run-123", {"eval_name": "test"})
    assert run.run_id == "test-run-123"
    assert run.metadata == {"eval_name": "test"}


def test_run_has_tracer():
    """Run initializes OpenTelemetry tracer."""
    run = ConcreteTestRun("test-run", {})
    assert run.tracer is not None


@pytest.mark.asyncio
async def test_run_save():
    """Run.save() returns storage path."""
    run = ConcreteTestRun("test-run-123", {"eval_name": "test"})
    path = await run.save()
    assert path == "test-path"


@pytest.mark.asyncio
async def test_run_load():
    """Run.load() retrieves run by ID."""
    run = await ConcreteTestRun.load("test-run-123")
    assert run.run_id == "test-run-123"


def test_run_artifacts_property():
    """Run.artifacts returns Dict[str, ArtifactRef]."""
    run = ConcreteTestRun("test-run", {})
    artifacts = run.artifacts
    assert isinstance(artifacts, dict)


def test_run_cannot_instantiate_directly():
    """Run ABC cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Run("test", {})  # type: ignore


# Config ABC Tests


def test_config_instantiation():
    """Config can be instantiated with config_path."""
    config = ConcreteTestConfig("/path/to/config.json")
    assert config.config_path == "/path/to/config.json"


def test_config_has_tracer():
    """Config initializes OpenTelemetry tracer."""
    config = ConcreteTestConfig("/path/to/config.json")
    assert config.tracer is not None


@pytest.mark.asyncio
async def test_config_load():
    """Config.load() returns configuration data."""
    config = ConcreteTestConfig("/path/to/config.json")
    data = await config.load()
    assert data == {"test": "data"}


@pytest.mark.asyncio
async def test_config_save():
    """Config.save() persists configuration data."""
    config = ConcreteTestConfig("/path/to/config.json")
    # Should not raise
    await config.save({"new": "data"})


def test_config_cannot_instantiate_directly():
    """Config ABC cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Config("/path/to/config.json")  # type: ignore


# Prompt ABC Tests


def test_prompt_instantiation():
    """Prompt can be instantiated with prompt_name and prompt_path."""
    prompt = ConcreteTestPrompt("assistant", "/prompts/assistant.toml")
    assert prompt.prompt_name == "assistant"
    assert prompt.prompt_path == "/prompts/assistant.toml"


def test_prompt_has_tracer():
    """Prompt initializes OpenTelemetry tracer."""
    prompt = ConcreteTestPrompt("assistant", "/prompts/")
    assert prompt.tracer is not None


@pytest.mark.asyncio
async def test_prompt_load():
    """Prompt.load() returns prompt content."""
    prompt = ConcreteTestPrompt("assistant", "/prompts/")
    content = await prompt.load("v1")
    assert content == "test prompt content"


@pytest.mark.asyncio
async def test_prompt_load_default_version():
    """Prompt.load() defaults to 'latest' version."""
    prompt = ConcreteTestPrompt("assistant", "/prompts/")
    content = await prompt.load()
    assert content == "test prompt content"


@pytest.mark.asyncio
async def test_prompt_save():
    """Prompt.save() persists prompt content."""
    prompt = ConcreteTestPrompt("assistant", "/prompts/")
    # Should not raise
    await prompt.save("v2", "new prompt content")


def test_prompt_cannot_instantiate_directly():
    """Prompt ABC cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Prompt("assistant", "/prompts/")  # type: ignore


# ArtifactRef Model Tests


def test_artifact_ref_model():
    """ArtifactRef validates and serializes correctly."""
    ref = ArtifactRef(path="results.jsonl", type="jsonl", size=1024)
    assert ref.path == "results.jsonl"
    assert ref.type == "jsonl"
    assert ref.size == 1024


def test_artifact_ref_extra_fields_ignored():
    """ArtifactRef ignores extra fields per ConfigDict(extra='ignore')."""
    ref = ArtifactRef(
        path="results.jsonl", type="jsonl", size=1024, unknown_field="ignored"
    )
    assert ref.path == "results.jsonl"
    # unknown_field should be ignored, not raise ValidationError
