import pytest

pytestmark = pytest.mark.unit
"""
Tests for Manifest model and config hashing.

Validates manifest metadata capture and deterministic config hashing
for run reproducibility.
"""

from datetime import datetime

import pytest

from gavel_ai.core.models import Manifest
from gavel_ai.storage.manifest import create_config_hash

# Manifest Model Tests


def test_manifest_model_creation():
    """Manifest can be created with all required fields."""
    manifest = Manifest(
        timestamp=datetime(2025, 12, 30, 12, 0, 0),
        config_hash="abc123",
        scenario_count=5,
        variant_count=2,
        judge_versions=[{"judge_id": "similarity", "version": "deepeval-0.21.0"}],
        status="completed",
        duration=45.2,
        metadata={"eval_name": "test", "custom": "value"},
    )

    assert manifest.timestamp == datetime(2025, 12, 30, 12, 0, 0)
    assert manifest.config_hash == "abc123"
    assert manifest.scenario_count == 5
    assert manifest.variant_count == 2
    assert len(manifest.judge_versions) == 1
    assert manifest.status == "completed"
    assert manifest.duration == 45.2
    assert manifest.metadata == {"eval_name": "test", "custom": "value"}


def test_manifest_status_must_be_valid():
    """Manifest status must be one of: completed, failed, partial."""
    # Valid statuses
    for status in ["completed", "failed", "partial"]:
        manifest = Manifest(
            timestamp=datetime.now(),
            config_hash="abc",
            scenario_count=1,
            variant_count=1,
            judge_versions=[],
            status=status,
            duration=1.0,
        )
        assert manifest.status == status

    # Invalid status should raise validation error
    with pytest.raises(Exception):  # Pydantic ValidationError
        Manifest(
            timestamp=datetime.now(),
            config_hash="abc",
            scenario_count=1,
            variant_count=1,
            judge_versions=[],
            status="invalid",
            duration=1.0,
        )


def test_manifest_metadata_defaults_to_empty_dict():
    """Manifest metadata field defaults to empty dict."""
    manifest = Manifest(
        timestamp=datetime.now(),
        config_hash="abc",
        scenario_count=1,
        variant_count=1,
        judge_versions=[],
        status="completed",
        duration=1.0,
    )
    assert manifest.metadata == {}


def test_manifest_json_serialization():
    """Manifest can be serialized to JSON."""
    manifest = Manifest(
        timestamp=datetime(2025, 12, 30, 12, 0, 0),
        config_hash="abc123",
        scenario_count=5,
        variant_count=2,
        judge_versions=[{"judge_id": "similarity", "version": "1.0"}],
        status="completed",
        duration=45.2,
        metadata={"eval_name": "test"},
    )

    json_data = manifest.model_dump(mode="json")
    assert json_data["config_hash"] == "abc123"
    assert json_data["scenario_count"] == 5
    assert json_data["status"] == "completed"


def test_manifest_from_json():
    """Manifest can be deserialized from JSON."""
    json_data = {
        "timestamp": "2025-12-30T12:00:00",
        "config_hash": "abc123",
        "scenario_count": 5,
        "variant_count": 2,
        "judge_versions": [{"judge_id": "similarity", "version": "1.0"}],
        "status": "completed",
        "duration": 45.2,
        "metadata": {"eval_name": "test"},
    }

    manifest = Manifest(**json_data)
    assert manifest.config_hash == "abc123"
    assert manifest.scenario_count == 5


def test_manifest_extra_fields_ignored():
    """Manifest ignores extra fields per ConfigDict(extra='ignore')."""
    manifest = Manifest(
        timestamp=datetime.now(),
        config_hash="abc",
        scenario_count=1,
        variant_count=1,
        judge_versions=[],
        status="completed",
        duration=1.0,
        unknown_field="ignored",
    )
    assert manifest.config_hash == "abc"


# Config Hashing Tests


def test_create_config_hash_deterministic():
    """create_config_hash produces same hash for same config."""
    config = {
        "eval_name": "test",
        "scenarios": [{"id": "s1", "input": "test"}],
        "agents": {"agent1": {"model": "claude"}},
    }

    hash1 = create_config_hash(config)
    hash2 = create_config_hash(config)

    assert hash1 == hash2


def test_create_config_hash_different_for_different_configs():
    """create_config_hash produces different hashes for different configs."""
    config1 = {"eval_name": "test1", "scenarios": [{"id": "s1"}]}
    config2 = {"eval_name": "test2", "scenarios": [{"id": "s1"}]}

    hash1 = create_config_hash(config1)
    hash2 = create_config_hash(config2)

    assert hash1 != hash2


def test_create_config_hash_ignores_key_order():
    """create_config_hash produces same hash regardless of key order."""
    config1 = {"a": 1, "b": 2, "c": 3}
    config2 = {"c": 3, "a": 1, "b": 2}

    hash1 = create_config_hash(config1)
    hash2 = create_config_hash(config2)

    assert hash1 == hash2


def test_create_config_hash_uses_sha256():
    """create_config_hash returns a SHA-256 hash (64 hex characters)."""
    config = {"test": "value"}
    hash_value = create_config_hash(config)

    assert len(hash_value) == 64  # SHA-256 produces 64 hex characters
    assert all(c in "0123456789abcdef" for c in hash_value)  # All hex chars


def test_create_config_hash_handles_nested_dicts():
    """create_config_hash handles nested dictionaries correctly."""
    config = {
        "level1": {
            "level2": {"level3": {"key": "value"}, "another": "data"},
            "sibling": "value",
        }
    }

    hash_value = create_config_hash(config)
    assert len(hash_value) == 64


def test_create_config_hash_handles_lists():
    """create_config_hash handles lists correctly."""
    config = {
        "scenarios": [
            {"id": "s1", "input": "test1"},
            {"id": "s2", "input": "test2"},
        ]
    }

    hash_value = create_config_hash(config)
    assert len(hash_value) == 64


def test_create_config_hash_handles_empty_config():
    """create_config_hash handles empty config."""
    config = {}
    hash_value = create_config_hash(config)
    assert len(hash_value) == 64


def test_create_config_hash_sensitive_to_list_order():
    """create_config_hash produces different hashes for different list orders."""
    config1 = {"items": ["a", "b", "c"]}
    config2 = {"items": ["c", "b", "a"]}

    hash1 = create_config_hash(config1)
    hash2 = create_config_hash(config2)

    # List order matters for reproducibility
    assert hash1 != hash2


def test_create_config_hash_consistent_across_runs():
    """create_config_hash produces same hash across multiple runs."""
    config = {
        "eval_name": "reproducibility_test",
        "scenarios": [{"id": "s1", "input": {"text": "test"}}],
        "agents": {"agent1": {"model": "claude", "temperature": 0.7}},
    }

    hashes = [create_config_hash(config) for _ in range(10)]

    # All hashes should be identical
    assert len(set(hashes)) == 1


# Integration Tests with Manifest


def test_manifest_with_real_config_hash():
    """Manifest can be created with real config hash."""
    config = {
        "eval_name": "test",
        "scenarios": [{"id": "s1"}],
        "agents": {"agent1": {"model": "claude"}},
    }
    config_hash = create_config_hash(config)

    manifest = Manifest(
        timestamp=datetime.now(),
        config_hash=config_hash,
        scenario_count=1,
        variant_count=1,
        judge_versions=[],
        status="completed",
        duration=10.5,
    )

    assert len(manifest.config_hash) == 64
    assert manifest.scenario_count == 1


def test_two_manifests_same_config_same_hash():
    """Two manifests with same config have same config_hash."""
    config = {
        "eval_name": "test",
        "scenarios": [{"id": "s1"}],
    }

    manifest1 = Manifest(
        timestamp=datetime.now(),
        config_hash=create_config_hash(config),
        scenario_count=1,
        variant_count=1,
        judge_versions=[],
        status="completed",
        duration=10.0,
    )

    manifest2 = Manifest(
        timestamp=datetime.now(),
        config_hash=create_config_hash(config),
        scenario_count=1,
        variant_count=1,
        judge_versions=[],
        status="completed",
        duration=15.0,
    )

    # Same config = same hash (reproducibility verification)
    assert manifest1.config_hash == manifest2.config_hash


def test_manifest_reproducibility_verification():
    """Manifests enable reproducibility verification via config_hash."""
    # Run 1 config
    run1_config = {
        "eval_name": "test",
        "scenarios": [{"id": "s1", "input": "test"}],
        "agents": {"agent1": {"model": "claude"}},
    }

    # Run 2 config (identical)
    run2_config = {
        "agents": {"agent1": {"model": "claude"}},  # Different key order
        "eval_name": "test",
        "scenarios": [{"id": "s1", "input": "test"}],
    }

    hash1 = create_config_hash(run1_config)
    hash2 = create_config_hash(run2_config)

    # Despite different key order, hashes match (reproducibility)
    assert hash1 == hash2
