"""
End-to-end integration tests for ScenarioProcessorStep with external+script test subjects.

Tests:
- success fixture → results_raw.jsonl records match schema shape
- nonzero_exit fixture → RunPolicyError raised with abort_on_exec_failure=True
- missing_response fixture → RunPolicyError raised
- warning_issue fixture → run continues with abort_on_process_error=False

Directory layout created in tmp_path per test:
    {eval_name}/
    ├── config/
    │   ├── eval_config.json   (test_subject_type=external, protocol=script)
    │   ├── agents.json
    └── data/
        └── scenarios.json
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.exceptions import RunPolicyError
from gavel_ai.core.steps.judge_runner import JudgeRunnerStep
from gavel_ai.core.steps.scenario_processor import ScenarioProcessorStep
from gavel_ai.models.runtime import JudgedRecord, OutputRecord

# Path to fixture scripts (checked-in under tests/fixtures/scripts/)
_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "scripts"


def _fixture_cmd(script_name: str) -> List[str]:
    """Build [sys.executable, <script_path>] for a fixture script."""
    return [sys.executable, str(_FIXTURES_DIR / script_name)]


def _make_script_eval_dir(
    tmp_path: Path,
    eval_name: str,
    scenarios: List[Dict[str, Any]],
    script_name: str = "success.py",
    system_id: str = "my-script-system",
    abort_on_exec_failure: bool = True,
    abort_on_process_error: bool = False,
    request_filename: str = "request.json",
    response_filename: str = "response.json",
) -> Path:
    """Create an eval directory configured for external+script execution."""
    config_dir = tmp_path / eval_name / "config"
    data_dir = tmp_path / eval_name / "data"
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    model_data: Dict[str, Any] = {
        "model_provider": "anthropic",
        "model_family": "claude",
        "model_version": "claude-test",
        "model_parameters": {"temperature": 0.0},
        "provider_auth": {"api_key": "sk-test"},
    }

    command: List[str] = _fixture_cmd(script_name)

    eval_config: Dict[str, Any] = {
        "eval_name": eval_name,
        "eval_type": "oneshot",
        "test_subject_type": "external",
        "test_subjects": [
            {
                "system_id": system_id,
                "protocol": "script",
                "config": {
                    "command": command,
                    "request_filename": request_filename,
                    "response_filename": response_filename,
                },
                "judges": [],
                "abort_on_exec_failure": abort_on_exec_failure,
                "abort_on_process_error": abort_on_process_error,
            }
        ],
        "variants": ["claude-test"],
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
    }
    (config_dir / "eval_config.json").write_text(json.dumps(eval_config))
    (config_dir / "agents.json").write_text(json.dumps({"_models": {"claude-test": model_data}}))
    (data_dir / "scenarios.json").write_text(json.dumps(scenarios))
    return tmp_path


def _make_run_ctx(
    eval_dir: Path,
    eval_name: str,
    tmp_path: Path,
    run_id: str = "run-script-001",
) -> LocalRunContext:
    eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root=eval_dir)
    return LocalRunContext(
        eval_ctx,
        base_dir=tmp_path / "runs",
        run_id=run_id,
        snapshot=False,
    )


@pytest.mark.integration
@pytest.mark.asyncio
class TestScenarioProcessorStepExternalScript:
    """End-to-end tests for ScenarioProcessorStep with protocol='script'."""

    async def test_success_script_produces_output_records(self, tmp_path: Path) -> None:
        """success.py → OutputRecord records with correct schema shape."""
        eval_name = "script-ok"
        scenarios = [
            {"id": "s1", "input": "hello", "expected_behavior": ""},
            {"id": "s2", "input": "world", "expected_behavior": ""},
        ]
        eval_dir = _make_script_eval_dir(tmp_path, eval_name, scenarios)
        run_ctx = _make_run_ctx(eval_dir, eval_name, tmp_path)
        logger = logging.getLogger("test")

        step = ScenarioProcessorStep(logger)
        await step.execute(run_ctx)

        assert run_ctx.processor_results is not None
        assert len(run_ctx.processor_results) == 2

        for record in run_ctx.processor_results:
            assert isinstance(record, OutputRecord)
            assert record.scenario_id in {"s1", "s2"}
            assert record.test_subject == "my-script-system"
            assert record.variant_id == "claude-test"
            assert record.timing_ms >= 0
            assert record.error is None
            # Output should be the result JSON from success.py
            assert "test_output" in record.processor_output

    async def test_results_raw_jsonl_records_match_schema(self, tmp_path: Path) -> None:
        """results_raw.jsonl records deserialize cleanly as OutputRecord."""
        eval_name = "script-jsonl"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": ""}]
        eval_dir = _make_script_eval_dir(tmp_path, eval_name, scenarios)
        run_ctx = _make_run_ctx(eval_dir, eval_name, tmp_path, run_id="run-jsonl-001")
        logger = logging.getLogger("test")

        step = ScenarioProcessorStep(logger)
        await step.execute(run_ctx)

        # Validate each appended record can round-trip as OutputRecord
        assert run_ctx.processor_results is not None
        for record in run_ctx.processor_results:
            # Re-validate from dict (simulates reading from jsonl)
            record_dict = record.model_dump()
            rehydrated = OutputRecord.model_validate(record_dict)
            assert rehydrated.scenario_id == record.scenario_id
            assert rehydrated.timing_ms == record.timing_ms

    async def test_nonzero_exit_raises_run_policy_error(self, tmp_path: Path) -> None:
        """nonzero_exit.py + abort_on_exec_failure=True → RunPolicyError."""
        eval_name = "script-fail"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": ""}]
        eval_dir = _make_script_eval_dir(
            tmp_path,
            eval_name,
            scenarios,
            script_name="nonzero_exit.py",
            abort_on_exec_failure=True,
        )
        run_ctx = _make_run_ctx(eval_dir, eval_name, tmp_path, run_id="run-fail-001")
        logger = logging.getLogger("test")

        step = ScenarioProcessorStep(logger)
        with pytest.raises(RunPolicyError):
            await step.execute(run_ctx)

    async def test_missing_response_raises_run_policy_error(self, tmp_path: Path) -> None:
        """missing_response.py + abort_on_exec_failure=True → RunPolicyError."""
        eval_name = "script-missing"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": ""}]
        eval_dir = _make_script_eval_dir(
            tmp_path,
            eval_name,
            scenarios,
            script_name="missing_response.py",
            abort_on_exec_failure=True,
        )
        run_ctx = _make_run_ctx(eval_dir, eval_name, tmp_path, run_id="run-missing-001")
        logger = logging.getLogger("test")

        step = ScenarioProcessorStep(logger)
        with pytest.raises(RunPolicyError):
            await step.execute(run_ctx)

    async def test_warning_issue_run_continues(self, tmp_path: Path) -> None:
        """warning_issue.py + abort_on_process_error=False → run completes without exception."""
        eval_name = "script-warning"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": ""}]
        eval_dir = _make_script_eval_dir(
            tmp_path,
            eval_name,
            scenarios,
            script_name="warning_issue.py",
            abort_on_exec_failure=True,
            abort_on_process_error=False,
        )
        run_ctx = _make_run_ctx(eval_dir, eval_name, tmp_path, run_id="run-warning-001")
        logger = logging.getLogger("test")

        step = ScenarioProcessorStep(logger)
        # Should NOT raise — warning-tier with abort_on_process_error=False
        await step.execute(run_ctx)

        assert run_ctx.processor_results is not None
        assert len(run_ctx.processor_results) == 1
        record = run_ctx.processor_results[0]
        assert record.error is not None  # error string is set
        assert record.metadata.get("external_tier") == "WARNING"

    async def test_single_scenario_output_record_fields(self, tmp_path: Path) -> None:
        """Single scenario → OutputRecord has all required schema fields populated."""
        eval_name = "script-fields"
        scenarios = [{"id": "scenario-abc", "input": {"key": "val"}, "expected_behavior": ""}]
        eval_dir = _make_script_eval_dir(tmp_path, eval_name, scenarios)
        run_ctx = _make_run_ctx(eval_dir, eval_name, tmp_path, run_id="run-fields-001")
        logger = logging.getLogger("test")

        step = ScenarioProcessorStep(logger)
        await step.execute(run_ctx)

        assert run_ctx.processor_results is not None
        record = run_ctx.processor_results[0]

        # Verify required OutputRecord fields
        assert record.scenario_id == "scenario-abc"
        assert record.test_subject != ""
        assert record.variant_id != ""
        assert record.timestamp != ""
        assert isinstance(record.tokens_prompt, int)
        assert isinstance(record.tokens_completion, int)
        assert isinstance(record.timing_ms, int) and record.timing_ms >= 0


# ---------------------------------------------------------------------------
# Helper: build an eval dir with external judge configured
# ---------------------------------------------------------------------------


def _make_script_eval_dir_with_judge(
    tmp_path: Path,
    eval_name: str,
    scenarios: List[Dict[str, Any]],
    task_script_name: str = "success.py",
    judge_script_name: str = "judge_success.py",
    judge_name: str = "my-ext-judge",
    judge_system_id: str = "ext-judge-v1",
    abort_on_exec_failure: bool = True,
    abort_on_process_error: bool = False,
) -> Path:
    """Create an eval directory configured for external task + external judge."""
    config_dir = tmp_path / eval_name / "config"
    data_dir = tmp_path / eval_name / "data"
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    model_data: Dict[str, Any] = {
        "model_provider": "anthropic",
        "model_family": "claude",
        "model_version": "claude-test",
        "model_parameters": {"temperature": 0.0},
        "provider_auth": {"api_key": "sk-test"},
    }

    task_command: List[str] = [sys.executable, str(_FIXTURES_DIR / task_script_name)]
    judge_command: List[str] = [sys.executable, str(_FIXTURES_DIR / judge_script_name)]

    eval_config: Dict[str, Any] = {
        "eval_name": eval_name,
        "eval_type": "oneshot",
        "test_subject_type": "external",
        "test_subjects": [
            {
                "system_id": "my-script-system",
                "protocol": "script",
                "config": {
                    "command": task_command,
                    "request_filename": "request.json",
                    "response_filename": "response.json",
                },
                "judges": [
                    {
                        "name": judge_name,
                        "type": "external",
                        "protocol": "script",
                        "system_id": judge_system_id,
                        "config": {
                            "command": judge_command,
                            "request_filename": "request.json",
                            "response_filename": "response.json",
                        },
                        "criteria": "Evaluate whether the output answers the question.",
                        "abort_on_exec_failure": abort_on_exec_failure,
                        "abort_on_process_error": abort_on_process_error,
                    }
                ],
                "abort_on_exec_failure": True,
                "abort_on_process_error": False,
            }
        ],
        "variants": ["claude-test"],
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
    }
    (config_dir / "eval_config.json").write_text(json.dumps(eval_config))
    (config_dir / "agents.json").write_text(json.dumps({"_models": {"claude-test": model_data}}))
    (data_dir / "scenarios.json").write_text(json.dumps(scenarios))
    return tmp_path


def _make_run_ctx_for_judging(
    eval_dir: Path,
    eval_name: str,
    tmp_path: Path,
    run_id: str,
) -> LocalRunContext:
    eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root=eval_dir)
    return LocalRunContext(
        eval_ctx,
        base_dir=tmp_path / "runs",
        run_id=run_id,
        snapshot=False,
    )


def _make_output_records(scenarios: List[Dict[str, Any]], test_subject: str = "my-script-system") -> List[OutputRecord]:
    """Create synthetic OutputRecord instances for judging tests."""
    ts = datetime.now(timezone.utc).isoformat()
    return [
        OutputRecord(
            test_subject=test_subject,
            variant_id="claude-test",
            scenario_id=s["id"],
            processor_output=f"response to: {s['input']}",
            timing_ms=10,
            tokens_prompt=5,
            tokens_completion=10,
            timestamp=ts,
        )
        for s in scenarios
    ]


@pytest.mark.integration
@pytest.mark.asyncio
class TestJudgeRunnerStepExternalScript:
    """End-to-end integration tests for JudgeRunnerStep with external+script judges."""

    async def test_script_judge_produces_judged_records(self, tmp_path: Path) -> None:
        """judge_success.py → JudgedRecord with judge_id, score, reasoning, trace_id."""
        eval_name = "judge-script-ok"
        scenarios = [
            {"id": "s1", "input": "what is 2+2?", "expected_behavior": "4"},
            {"id": "s2", "input": "what is the sky?", "expected_behavior": "blue"},
        ]
        eval_dir = _make_script_eval_dir_with_judge(tmp_path, eval_name, scenarios)
        run_ctx = _make_run_ctx_for_judging(eval_dir, eval_name, tmp_path, run_id="run-judge-001")
        logger = logging.getLogger("test")

        # Pre-populate processor_results (normally set by ScenarioProcessorStep)
        run_ctx.processor_results = _make_output_records(scenarios)

        step = JudgeRunnerStep(logger)
        await step.execute(run_ctx)

        assert run_ctx.external_judged_records is not None
        assert len(run_ctx.external_judged_records) == 2

        for record in run_ctx.external_judged_records:
            assert isinstance(record, JudgedRecord)
            assert record.judge_id == "ext-judge-v1"
            assert record.score == 8
            assert record.reasoning == "The output looks good based on the criteria."
            assert record.error is None
            assert record.timestamp != ""
            assert "trace_id" in record.metadata

    async def test_script_judge_judged_record_has_expected_shape(self, tmp_path: Path) -> None:
        """JudgedRecord from external judge has all required schema fields."""
        eval_name = "judge-script-shape"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": "world"}]
        eval_dir = _make_script_eval_dir_with_judge(tmp_path, eval_name, scenarios)
        run_ctx = _make_run_ctx_for_judging(eval_dir, eval_name, tmp_path, run_id="run-judge-shape-001")
        logger = logging.getLogger("test")

        run_ctx.processor_results = _make_output_records(scenarios)

        step = JudgeRunnerStep(logger)
        await step.execute(run_ctx)

        assert len(run_ctx.external_judged_records) == 1
        rec = run_ctx.external_judged_records[0]

        # Verify all JudgedRecord fields are present and correctly typed
        assert rec.test_subject == "my-script-system"
        assert rec.variant_id == "claude-test"
        assert rec.scenario_id == "s1"
        assert rec.judge_id == "ext-judge-v1"
        assert isinstance(rec.score, int) and 1 <= rec.score <= 10
        assert rec.error is None
        assert isinstance(rec.timestamp, str) and rec.timestamp != ""
        assert isinstance(rec.metadata, dict)
        assert "trace_id" in rec.metadata

    async def test_script_judge_nonzero_exit_raises_run_policy_error(self, tmp_path: Path) -> None:
        """judge_nonzero_exit.py + abort_on_exec_failure=True → RunPolicyError."""
        eval_name = "judge-script-fail"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": "world"}]
        eval_dir = _make_script_eval_dir_with_judge(
            tmp_path,
            eval_name,
            scenarios,
            judge_script_name="judge_nonzero_exit.py",
            abort_on_exec_failure=True,
        )
        run_ctx = _make_run_ctx_for_judging(eval_dir, eval_name, tmp_path, run_id="run-judge-fail-001")
        logger = logging.getLogger("test")

        run_ctx.processor_results = _make_output_records(scenarios)

        step = JudgeRunnerStep(logger)
        with pytest.raises(RunPolicyError):
            await step.execute(run_ctx)

    async def test_script_judge_warning_issue_continues(self, tmp_path: Path) -> None:
        """judge_warning_issue.py + abort_on_process_error=False → run continues."""
        eval_name = "judge-script-warning"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": "world"}]
        eval_dir = _make_script_eval_dir_with_judge(
            tmp_path,
            eval_name,
            scenarios,
            judge_script_name="judge_warning_issue.py",
            abort_on_exec_failure=True,
            abort_on_process_error=False,
        )
        run_ctx = _make_run_ctx_for_judging(eval_dir, eval_name, tmp_path, run_id="run-judge-warning-001")
        logger = logging.getLogger("test")

        run_ctx.processor_results = _make_output_records(scenarios)

        step = JudgeRunnerStep(logger)
        # Should NOT raise — warning-tier with abort_on_process_error=False
        await step.execute(run_ctx)

        assert len(run_ctx.external_judged_records) == 1
        rec = run_ctx.external_judged_records[0]
        assert rec.error is not None  # error string is set for PROCESS_SUCCESS_WITH_ISSUE
        assert rec.metadata.get("external_tier") == "WARNING"

    async def test_script_judge_records_have_no_schema_shape_difference_from_inprocess(
        self, tmp_path: Path
    ) -> None:
        """Externally-delegated JudgedRecords have same field set as in-process judge output."""
        eval_name = "judge-script-diffed"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": "world"}]
        eval_dir = _make_script_eval_dir_with_judge(tmp_path, eval_name, scenarios)
        run_ctx = _make_run_ctx_for_judging(eval_dir, eval_name, tmp_path, run_id="run-judge-diff-001")
        logger = logging.getLogger("test")

        run_ctx.processor_results = _make_output_records(scenarios)

        step = JudgeRunnerStep(logger)
        await step.execute(run_ctx)

        assert len(run_ctx.external_judged_records) == 1
        ext_rec = run_ctx.external_judged_records[0]

        # Build an in-process-style JudgedRecord with the same structural fields
        inprocess_rec = JudgedRecord(
            test_subject="my-script-system",
            variant_id="claude-test",
            scenario_id="s1",
            judge_id="some-inprocess-judge",
            score=7,
            reasoning="in-process reasoning",
            error=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={},
        )

        # The field names should be identical (same schema shape)
        ext_keys = set(ext_rec.model_dump().keys())
        inprocess_keys = set(inprocess_rec.model_dump().keys())
        assert ext_keys == inprocess_keys, (
            f"Schema shape mismatch: external has {ext_keys - inprocess_keys} extra, "
            f"in-process has {inprocess_keys - ext_keys} extra"
        )
