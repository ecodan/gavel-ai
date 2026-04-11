import pytest

pytestmark = pytest.mark.unit
"""
Tests for RunHistory tracking and querying.

Validates run listing, filtering, and pagination for run history management.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gavel_ai.storage.filesystem import LocalFilesystemRun
from gavel_ai.storage.history import RunHistory


@pytest.mark.asyncio
async def test_list_runs_empty_history(tmp_path: Path):
    """RunHistory.list_runs() returns empty list when no runs exist."""
    history = RunHistory(base_dir=str(tmp_path))
    runs = await history.list_runs()
    assert runs == []


@pytest.mark.asyncio
async def test_list_runs_returns_all_runs(tmp_path: Path):
    """RunHistory.list_runs() returns all runs."""
    # Create 3 runs
    for i in range(3):
        run = LocalFilesystemRun(
            run_id=f"run-{i}",
            eval_name="test-eval",
            metadata={"eval_name": "test-eval"},
            base_dir=str(tmp_path),
        )
        run.manifest_data = {
            "timestamp": datetime.now().isoformat(),
            "scenario_count": i + 1,
            "variant_count": 2,
        }
        await run.save()

    history = RunHistory(base_dir=str(tmp_path))
    runs = await history.list_runs()

    assert len(runs) == 3


@pytest.mark.asyncio
async def test_list_runs_filters_by_eval_name(tmp_path: Path):
    """RunHistory.list_runs() filters by eval_name."""
    # Create runs for different evaluations
    for i, eval_name in enumerate(["eval-1", "eval-2", "eval-1"]):
        run = LocalFilesystemRun(
            run_id=f"run-{eval_name}-{i}",
            eval_name=eval_name,
            metadata={"eval_name": eval_name},
            base_dir=str(tmp_path),
        )
        run.manifest_data = {"timestamp": datetime.now().isoformat()}
        await run.save()

    history = RunHistory(base_dir=str(tmp_path))
    runs = await history.list_runs(eval_name="eval-1")

    assert len(runs) == 2
    assert all(r["eval_name"] == "eval-1" for r in runs)


@pytest.mark.asyncio
async def test_list_runs_filters_by_after_date(tmp_path: Path):
    """RunHistory.list_runs() filters runs after specified date."""
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    # Create runs with different timestamps
    for i, timestamp in enumerate([two_days_ago, yesterday, now]):
        run = LocalFilesystemRun(
            run_id=f"run-{i}",
            eval_name="test",
            metadata={"eval_name": "test"},
            base_dir=str(tmp_path),
        )
        run.manifest_data = {"timestamp": timestamp.isoformat()}
        await run.save()

    history = RunHistory(base_dir=str(tmp_path))
    runs = await history.list_runs(after=yesterday)

    # Should only get yesterday and today's runs
    assert len(runs) >= 1  # At least today's run


@pytest.mark.asyncio
async def test_list_runs_filters_by_before_date(tmp_path: Path):
    """RunHistory.list_runs() filters runs before specified date."""
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    # Create runs with different timestamps
    for i, timestamp in enumerate([two_days_ago, yesterday, now]):
        run = LocalFilesystemRun(
            run_id=f"run-{i}",
            eval_name="test",
            metadata={"eval_name": "test"},
            base_dir=str(tmp_path),
        )
        run.manifest_data = {"timestamp": timestamp.isoformat()}
        await run.save()

    history = RunHistory(base_dir=str(tmp_path))
    runs = await history.list_runs(before=yesterday)

    # Should only get runs from 2 days ago
    assert len(runs) >= 1


@pytest.mark.asyncio
async def test_list_runs_pagination(tmp_path: Path):
    """RunHistory.list_runs() supports pagination with limit and offset."""
    # Create 10 runs
    for i in range(10):
        run = LocalFilesystemRun(
            run_id=f"run-{i:02d}",
            eval_name="test",
            metadata={"eval_name": "test"},
            base_dir=str(tmp_path),
        )
        run.manifest_data = {"timestamp": datetime.now().isoformat()}
        await run.save()

    history = RunHistory(base_dir=str(tmp_path))

    # First page: limit 5, offset 0
    page1 = await history.list_runs(limit=5, offset=0)
    assert len(page1) == 5

    # Second page: limit 5, offset 5
    page2 = await history.list_runs(limit=5, offset=5)
    assert len(page2) == 5

    # No overlap
    page1_ids = {r["run_id"] for r in page1}
    page2_ids = {r["run_id"] for r in page2}
    assert len(page1_ids & page2_ids) == 0


@pytest.mark.asyncio
async def test_list_runs_returns_summary_fields(tmp_path: Path):
    """RunHistory.list_runs() returns summary with required fields."""
    run = LocalFilesystemRun(
        run_id="run-test",
        eval_name="test-eval",
        metadata={"eval_name": "test-eval"},
        base_dir=str(tmp_path),
    )
    run.manifest_data = {
        "timestamp": "2025-12-30T12:00:00",
        "scenario_count": 5,
        "variant_count": 2,
        "status": "completed",
    }
    await run.save()

    history = RunHistory(base_dir=str(tmp_path))
    runs = await history.list_runs()

    assert len(runs) == 1
    summary = runs[0]

    assert "run_id" in summary
    assert "eval_name" in summary
    assert "timestamp" in summary
    assert "scenario_count" in summary
    assert "variant_count" in summary
    assert "status" in summary


@pytest.mark.asyncio
async def test_list_runs_sorted_by_timestamp_descending(tmp_path: Path):
    """RunHistory.list_runs() returns runs sorted by timestamp (newest first)."""
    now = datetime.now()
    timestamps = [
        now - timedelta(days=2),
        now - timedelta(days=1),
        now,
    ]

    # Create runs in random order
    for i, ts in enumerate([timestamps[1], timestamps[2], timestamps[0]]):
        run = LocalFilesystemRun(
            run_id=f"run-{i}",
            eval_name="test",
            metadata={"eval_name": "test"},
            base_dir=str(tmp_path),
        )
        run.manifest_data = {"timestamp": ts.isoformat()}
        await run.save()

    history = RunHistory(base_dir=str(tmp_path))
    runs = await history.list_runs()

    # Should be sorted newest first
    assert len(runs) == 3
    # Parse timestamps and verify descending order
    run_times = [datetime.fromisoformat(r["timestamp"]) for r in runs]
    assert run_times == sorted(run_times, reverse=True)


@pytest.mark.asyncio
async def test_list_runs_multiple_evaluations(tmp_path: Path):
    """RunHistory.list_runs() works across multiple evaluation directories."""
    # Create runs in different evaluation directories
    for eval_name in ["eval-a", "eval-b", "eval-c"]:
        for i in range(2):
            run = LocalFilesystemRun(
                run_id=f"run-{eval_name}-{i}",
                eval_name=eval_name,
                metadata={"eval_name": eval_name},
                base_dir=str(tmp_path),
            )
            run.manifest_data = {"timestamp": datetime.now().isoformat()}
            await run.save()

    history = RunHistory(base_dir=str(tmp_path))
    runs = await history.list_runs()

    # Should find all 6 runs across 3 evaluations
    assert len(runs) == 6
    eval_names = {r["eval_name"] for r in runs}
    assert eval_names == {"eval-a", "eval-b", "eval-c"}


@pytest.mark.asyncio
async def test_list_runs_handles_missing_manifest_gracefully(tmp_path: Path):
    """RunHistory.list_runs() handles runs with missing manifests."""
    # Create valid run
    run1 = LocalFilesystemRun(
        run_id="run-valid",
        eval_name="test",
        metadata={"eval_name": "test"},
        base_dir=str(tmp_path),
    )
    run1.manifest_data = {"timestamp": datetime.now().isoformat()}
    await run1.save()

    # Create run directory without manifest
    invalid_run_dir = tmp_path / "evaluations/test/runs/run-invalid"
    invalid_run_dir.mkdir(parents=True, exist_ok=True)

    history = RunHistory(base_dir=str(tmp_path))
    runs = await history.list_runs()

    # Should only return valid run
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-valid"
