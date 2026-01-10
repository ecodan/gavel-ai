"""
Tests for LocalFilesystemRun storage implementation.

Validates filesystem-based Run implementation with isolated tmp_path fixtures.
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from gavel_ai.core.exceptions import StorageError
from gavel_ai.core.models import ArtifactRef
from gavel_ai.storage.filesystem import LocalFilesystemRun


# Initialization and Directory Structure Tests


def test_filesystem_run_init(tmp_path: Path):
    """LocalFilesystemRun initializes with correct attributes."""
    run = LocalFilesystemRun(
        run_id="run-20251230-120000",
        eval_name="test-eval",
        metadata={"eval_name": "test-eval", "timestamp": "2025-12-30T12:00:00"},
        base_dir=str(tmp_path),
    )

    assert run.run_id == "run-20251230-120000"
    assert run.eval_name == "test-eval"
    assert run.metadata == {"eval_name": "test-eval", "timestamp": "2025-12-30T12:00:00"}
    assert run.base_dir == tmp_path
    assert run.run_dir == tmp_path / "evaluations/test-eval/runs/run-20251230-120000"


def test_filesystem_run_default_base_dir():
    """LocalFilesystemRun uses .gavel as default base_dir."""
    run = LocalFilesystemRun(run_id="run-test", eval_name="test", metadata={})
    assert run.base_dir == Path(".gavel")


# Save Method Tests


@pytest.mark.asyncio
async def test_save_creates_directory_structure(tmp_path: Path):
    """LocalFilesystemRun.save() creates correct directory structure."""
    run = LocalFilesystemRun(
        run_id="run-20251230-120000",
        eval_name="test-eval",
        metadata={"eval_name": "test-eval"},
        base_dir=str(tmp_path),
    )

    path = await run.save()

    expected_dir = tmp_path / "evaluations/test-eval/runs/run-20251230-120000"
    assert expected_dir.exists()
    assert expected_dir.is_dir()
    assert (expected_dir / "config").exists()
    assert (expected_dir / "config").is_dir()
    assert path == str(expected_dir)


@pytest.mark.asyncio
async def test_save_creates_all_artifacts(tmp_path: Path):
    """LocalFilesystemRun.save() creates all required artifacts."""
    run = LocalFilesystemRun(
        run_id="run-test",
        eval_name="test",
        metadata={
            "eval_name": "test",
            "timestamp": "2025-12-30T12:00:00",
            "config_hash": "abc123",
        },
        base_dir=str(tmp_path),
    )

    # Add some data to artifacts
    run.manifest_data = {"version": "1.0", "run_id": "run-test"}
    run.config_data = {"eval_config": {"name": "test"}}
    run.telemetry_data = [{"event": "start", "timestamp": "2025-12-30T12:00:00"}]
    run.results_data = [{"scenario_id": "s1", "score": 8}]
    run.metadata_data = {"duration": 120}
    run.log_data = "2025-12-30 12:00:00 [INFO] Test started\n"
    run.report_data = "<html><body>Test Report</body></html>"

    await run.save()

    run_dir = tmp_path / "evaluations/test/runs/run-test"
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "config" / "eval_config.json").exists()
    assert (run_dir / "telemetry.jsonl").exists()
    assert (run_dir / "results.jsonl").exists()
    assert (run_dir / "run_metadata.json").exists()
    assert (run_dir / "gavel.log").exists()
    assert (run_dir / "report.html").exists()


@pytest.mark.asyncio
async def test_save_handles_missing_artifacts_gracefully(tmp_path: Path):
    """LocalFilesystemRun.save() handles missing optional artifacts."""
    run = LocalFilesystemRun(
        run_id="run-minimal",
        eval_name="test",
        metadata={"eval_name": "test"},
        base_dir=str(tmp_path),
    )

    # Don't set any artifact data
    await run.save()

    # Directory created but some artifacts may be empty/missing
    run_dir = tmp_path / "evaluations/test/runs/run-minimal"
    assert run_dir.exists()


# Load Method Tests


@pytest.mark.asyncio
async def test_load_reconstructs_run(tmp_path: Path):
    """LocalFilesystemRun.load() reconstructs saved run."""
    # Save a run
    original = LocalFilesystemRun(
        run_id="run-loadtest",
        eval_name="eval-test",
        metadata={"eval_name": "eval-test", "key": "value"},
        base_dir=str(tmp_path),
    )
    original.manifest_data = {"version": "1.0"}
    original.config_data = {"eval_config": {"name": "test"}}
    original.telemetry_data = [{"event": "start"}]
    original.results_data = [{"scenario_id": "s1"}]
    original.metadata_data = {"duration": 100}
    original.log_data = "Log line\n"
    original.report_data = "<html></html>"

    await original.save()

    # Load it back
    loaded = await LocalFilesystemRun.load("run-loadtest", str(tmp_path))

    assert loaded.run_id == "run-loadtest"
    assert loaded.eval_name == "eval-test"
    assert loaded.metadata == {"eval_name": "eval-test", "key": "value"}
    assert loaded.manifest_data == {"version": "1.0"}
    assert loaded.config_data == {"eval_config": {"name": "test"}}


@pytest.mark.asyncio
async def test_load_raises_storage_error_if_not_found(tmp_path: Path):
    """LocalFilesystemRun.load() raises StorageError if run not found."""
    with pytest.raises(StorageError, match="Run nonexistent not found"):
        await LocalFilesystemRun.load("nonexistent", str(tmp_path))


@pytest.mark.asyncio
async def test_load_finds_run_in_any_evaluation(tmp_path: Path):
    """LocalFilesystemRun.load() finds run regardless of eval_name."""
    # Create run in specific eval
    run = LocalFilesystemRun(
        run_id="run-anywhere",
        eval_name="some-eval",
        metadata={"test": "data"},
        base_dir=str(tmp_path),
    )
    await run.save()

    # Load without knowing eval_name
    loaded = await LocalFilesystemRun.load("run-anywhere", str(tmp_path))

    assert loaded.run_id == "run-anywhere"
    assert loaded.eval_name == "some-eval"


# Artifacts Property Tests


def test_artifacts_property_empty_initially(tmp_path: Path):
    """LocalFilesystemRun.artifacts returns empty dict initially."""
    run = LocalFilesystemRun(
        run_id="run-test", eval_name="test", metadata={}, base_dir=str(tmp_path)
    )
    assert run.artifacts == {}


@pytest.mark.asyncio
async def test_artifacts_property_populated_after_save(tmp_path: Path):
    """LocalFilesystemRun.artifacts populated after save."""
    run = LocalFilesystemRun(
        run_id="run-artifacts",
        eval_name="test",
        metadata={"test": "data"},
        base_dir=str(tmp_path),
    )
    run.manifest_data = {"version": "1.0"}
    run.config_data = {"config": "data"}

    await run.save()

    artifacts = run.artifacts
    assert "manifest" in artifacts
    assert isinstance(artifacts["manifest"], ArtifactRef)
    assert artifacts["manifest"].type == "json"
    assert artifacts["manifest"].size > 0


# Individual Artifact Save/Load Tests


@pytest.mark.asyncio
async def test_save_manifest(tmp_path: Path):
    """save_manifest() writes manifest.json correctly."""
    run = LocalFilesystemRun(
        run_id="run-test", eval_name="test", metadata={}, base_dir=str(tmp_path)
    )
    run.run_dir.mkdir(parents=True, exist_ok=True)
    run.manifest_data = {
        "version": "1.0",
        "run_id": "run-test",
        "timestamp": "2025-12-30T12:00:00",
    }

    await run.save_manifest()

    manifest_path = run.run_dir / "manifest.json"
    assert manifest_path.exists()

    with open(manifest_path) as f:
        data = json.load(f)
    assert data["version"] == "1.0"
    assert data["run_id"] == "run-test"


@pytest.mark.asyncio
async def test_save_config(tmp_path: Path):
    """save_config() writes config files correctly."""
    run = LocalFilesystemRun(
        run_id="run-test", eval_name="test", metadata={}, base_dir=str(tmp_path)
    )
    (run.run_dir / "config").mkdir(parents=True, exist_ok=True)
    run.config_data = {
        "eval_config": {"name": "test"},
        "agents": {"agent1": {"model": "claude"}},
    }

    await run.save_config()

    eval_config_path = run.run_dir / "config" / "eval_config.json"
    assert eval_config_path.exists()

    with open(eval_config_path) as f:
        data = json.load(f)
    assert data["name"] == "test"


@pytest.mark.asyncio
async def test_save_telemetry(tmp_path: Path):
    """save_telemetry() writes telemetry.jsonl correctly."""
    run = LocalFilesystemRun(
        run_id="run-test", eval_name="test", metadata={}, base_dir=str(tmp_path)
    )
    run.run_dir.mkdir(parents=True, exist_ok=True)
    run.telemetry_data = [
        {"event": "start", "timestamp": "2025-12-30T12:00:00"},
        {"event": "end", "timestamp": "2025-12-30T12:05:00"},
    ]

    await run.save_telemetry()

    telemetry_path = run.run_dir / "telemetry.jsonl"
    assert telemetry_path.exists()

    with open(telemetry_path) as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "start"


@pytest.mark.asyncio
async def test_save_results(tmp_path: Path):
    """save_results() writes results.jsonl correctly."""
    run = LocalFilesystemRun(
        run_id="run-test", eval_name="test", metadata={}, base_dir=str(tmp_path)
    )
    run.run_dir.mkdir(parents=True, exist_ok=True)
    run.results_data = [
        {"scenario_id": "s1", "score": 8},
        {"scenario_id": "s2", "score": 9},
    ]

    await run.save_results()

    results_path = run.run_dir / "results.jsonl"
    assert results_path.exists()

    with open(results_path) as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["score"] == 8


@pytest.mark.asyncio
async def test_load_manifest(tmp_path: Path):
    """load_manifest() reads manifest.json correctly."""
    run = LocalFilesystemRun(
        run_id="run-test", eval_name="test", metadata={}, base_dir=str(tmp_path)
    )
    run.run_dir.mkdir(parents=True, exist_ok=True)

    # Write manifest manually
    manifest_data = {"version": "1.0", "run_id": "run-test"}
    with open(run.run_dir / "manifest.json", "w") as f:
        json.dump(manifest_data, f, indent=2)

    await run.load_manifest()

    assert run.manifest_data == manifest_data


@pytest.mark.asyncio
async def test_load_config(tmp_path: Path):
    """load_config() reads config files correctly."""
    run = LocalFilesystemRun(
        run_id="run-test", eval_name="test", metadata={}, base_dir=str(tmp_path)
    )
    config_dir = run.run_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write config file manually
    eval_config = {"name": "test", "version": "1.0"}
    with open(config_dir / "eval_config.json", "w") as f:
        json.dump(eval_config, f, indent=2)

    await run.load_config()

    assert "eval_config" in run.config_data
    assert run.config_data["eval_config"]["name"] == "test"


@pytest.mark.asyncio
async def test_load_telemetry(tmp_path: Path):
    """load_telemetry() reads telemetry.jsonl correctly."""
    run = LocalFilesystemRun(
        run_id="run-test", eval_name="test", metadata={}, base_dir=str(tmp_path)
    )
    run.run_dir.mkdir(parents=True, exist_ok=True)

    # Write telemetry manually
    with open(run.run_dir / "telemetry.jsonl", "w") as f:
        f.write('{"event": "start"}\n')
        f.write('{"event": "end"}\n')

    await run.load_telemetry()

    assert len(run.telemetry_data) == 2
    assert run.telemetry_data[0]["event"] == "start"


@pytest.mark.asyncio
async def test_save_and_load_round_trip(tmp_path: Path):
    """Save and load produce identical data."""
    original = LocalFilesystemRun(
        run_id="run-roundtrip",
        eval_name="test",
        metadata={"key": "value"},
        base_dir=str(tmp_path),
    )
    original.manifest_data = {"version": "1.0"}
    original.config_data = {"eval_config": {"name": "test"}}
    original.telemetry_data = [{"event": "start"}]
    original.results_data = [{"scenario_id": "s1", "score": 8}]
    original.metadata_data = {"duration": 100}
    original.log_data = "Test log\n"
    original.report_data = "<html>Report</html>"

    await original.save()

    loaded = await LocalFilesystemRun.load("run-roundtrip", str(tmp_path))

    assert loaded.manifest_data == original.manifest_data
    assert loaded.config_data == original.config_data
    assert loaded.telemetry_data == original.telemetry_data
    assert loaded.results_data == original.results_data
    assert loaded.metadata_data == original.metadata_data
    assert loaded.log_data == original.log_data
    assert loaded.report_data == original.report_data


# Error Handling Tests


@pytest.mark.asyncio
async def test_save_raises_storage_error_on_permission_error(tmp_path: Path, monkeypatch):
    """LocalFilesystemRun.save() raises StorageError on permission errors."""
    run = LocalFilesystemRun(
        run_id="run-perms",
        eval_name="test",
        metadata={},
        base_dir=str(tmp_path),
    )

    # Mock mkdir to raise PermissionError
    def mock_mkdir(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    with pytest.raises(StorageError, match="Failed to save run"):
        await run.save()


@pytest.mark.asyncio
async def test_load_raises_storage_error_on_corrupt_metadata(tmp_path: Path):
    """LocalFilesystemRun.load() raises StorageError on corrupt metadata."""
    # Create run directory manually with corrupt metadata
    run_dir = tmp_path / "evaluations/test/runs/run-corrupt"
    run_dir.mkdir(parents=True)

    # Write invalid JSON
    with open(run_dir / "run_metadata.json", "w") as f:
        f.write("{ invalid json }")

    with pytest.raises(StorageError, match="Failed to load"):
        await LocalFilesystemRun.load("run-corrupt", str(tmp_path))


# Tracer Tests


def test_run_has_tracer(tmp_path: Path):
    """LocalFilesystemRun initializes OpenTelemetry tracer."""
    run = LocalFilesystemRun(
        run_id="run-test", eval_name="test", metadata={}, base_dir=str(tmp_path)
    )
    assert run.tracer is not None
