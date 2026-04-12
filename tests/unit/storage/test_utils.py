import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for storage.utils.
"""

import json
from pathlib import Path

import pytest

from gavel_ai.storage.utils import compute_config_hash


class TestComputeConfigHash:
    """Tests for compute_config_hash utility function."""

    def test_compute_config_hash_returns_consistent_hash(self, tmp_path: Path):
        """compute_config_hash returns consistent SHA256 hash."""
        config1 = tmp_path / "config1.json"
        config1.write_text(json.dumps({"key": "value"}))

        hash1 = compute_config_hash({"config": config1})
        hash2 = compute_config_hash({"config": config1})

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_compute_config_hash_deterministic_ordering(self, tmp_path: Path):
        """compute_config_hash uses deterministic key ordering."""
        file1 = tmp_path / "file1.json"
        file1.write_text(json.dumps({"a": 1}))

        file2 = tmp_path / "file2.json"
        file2.write_text(json.dumps({"b": 2}))

        # Order shouldn't matter
        hash1 = compute_config_hash({"file1": file1, "file2": file2})
        hash2 = compute_config_hash({"file2": file2, "file1": file1})

        assert hash1 == hash2

    def test_compute_config_hash_different_for_different_content(self, tmp_path: Path):
        """compute_config_hash returns different hashes for different content."""
        file1 = tmp_path / "file1.json"
        file1.write_text(json.dumps({"key": "value1"}))

        file2 = tmp_path / "file2.json"
        file2.write_text(json.dumps({"key": "value2"}))

        hash1 = compute_config_hash({"config": file1})
        hash2 = compute_config_hash({"config": file2})

        assert hash1 != hash2

    def test_compute_config_hash_raises_file_not_found(self, tmp_path: Path):
        """compute_config_hash raises FileNotFoundError for missing files."""
        nonexistent = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            compute_config_hash({"config": nonexistent})

    def test_compute_config_hash_handles_multiple_files(self, tmp_path: Path):
        """compute_config_hash handles multiple config files."""
        file1 = tmp_path / "agents.json"
        file1.write_text(json.dumps({"agents": {}}))

        file2 = tmp_path / "eval_config.json"
        file2.write_text(json.dumps({"eval": {}}))

        file3 = tmp_path / "scenarios.json"
        file3.write_text(json.dumps({"scenarios": []}))

        hash_result = compute_config_hash(
            {
                "agents": file1,
                "eval_config": file2,
                "scenarios": file3,
            }
        )

        assert len(hash_result) == 64
        assert hash_result.isalnum()  # Valid hex string
