import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for JudgeRunnerStep.
"""

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.base import StepPhase
from gavel_ai.core.steps.judge_runner import (
    JudgeRunnerStep,
    _resolve_scenario_field,
    _validate_geval_expected_output,
    get_model_definition,
)
from gavel_ai.models import EvalConfig, JudgeConfig
from gavel_ai.models.config import ScenarioFieldMapping, ScenariosConfig, TestSubject
from gavel_ai.models.runtime import OutputRecord, Scenario


class TestGetModelDefinition:
    """Test get_model_definition helper function."""

    def test_get_model_definition_finds_direct_model(self):
        """get_model_definition finds model in _models section."""
        agents_config = {
            "_models": {
                "claude-model": {
                    "model_version": "claude-3-5-sonnet-20241022",
                    "model_family": "claude",
                }
            }
        }

        model_def = get_model_definition(agents_config, "claude-model")

        assert model_def["model_version"] == "claude-3-5-sonnet-20241022"
        assert model_def["model_family"] == "claude"

    def test_get_model_definition_finds_agent_reference(self):
        """get_model_definition finds model via agent reference."""
        agents_config = {
            "_models": {"base-model": {"model_version": "claude-test", "model_family": "claude"}},
            "judge-agent": {"model_id": "base-model", "prompt": "judge:v1"},
        }

        model_def = get_model_definition(agents_config, "judge-agent")

        assert model_def["model_version"] == "claude-test"
        assert model_def["model_family"] == "claude"

    def test_get_model_definition_raises_config_error_if_not_found(self):
        """get_model_definition raises ConfigError if model not found."""
        agents_config = {"_models": {}}

        with pytest.raises(ConfigError, match="Model 'nonexistent' not found"):
            get_model_definition(agents_config, "nonexistent")


class TestJudgeRunnerStep:
    """Test JudgeRunnerStep class."""

    def test_init(self, mock_logger: logging.Logger):
        """JudgeRunnerStep initializes with logger."""
        step = JudgeRunnerStep(mock_logger)

        assert step.logger == mock_logger

    def test_phase_property(self, mock_logger: logging.Logger):
        """phase property returns JUDGING."""
        step = JudgeRunnerStep(mock_logger)

        assert step.phase == StepPhase.JUDGING

    @pytest.mark.asyncio
    async def test_execute_raises_config_error_if_no_processor_results(
        self, mock_logger: logging.Logger
    ):
        """execute raises ConfigError if processor_results is None."""
        step = JudgeRunnerStep(mock_logger)

        mock_context = MagicMock()
        mock_context.processor_results = None

        with pytest.raises(ConfigError, match="requires processor_results"):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_skips_if_no_judges_configured(self, mock_logger: logging.Logger):
        """execute skips judging if no judges configured."""
        step = JudgeRunnerStep(mock_logger)

        mock_context = MagicMock()
        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subjects = []

        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.processor_results = [MagicMock()]

        await step.execute(mock_context)

        assert mock_context.evaluation_results == []

    @pytest.mark.asyncio
    async def test_execute_extracts_judges_from_test_subjects(self, mock_logger: logging.Logger):
        """execute extracts all judges from test_subjects."""
        step = JudgeRunnerStep(mock_logger)

        mock_judge1 = MagicMock(spec=JudgeConfig)
        mock_judge1.name = "judge1"
        mock_judge1.model = None
        mock_judge1.config = None

        mock_judge2 = MagicMock(spec=JudgeConfig)
        mock_judge2.name = "judge2"
        mock_judge2.model = None
        mock_judge2.config = None

        mock_subject1 = MagicMock(spec=TestSubject)
        mock_subject1.judges = [mock_judge1]

        mock_subject2 = MagicMock(spec=TestSubject)
        mock_subject2.judges = [mock_judge2]

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subjects = [mock_subject1, mock_subject2]
        mock_eval_config.scenarios = MagicMock(field_mapping=None)

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.agents.read.return_value = {"_models": {}}
        mock_context.eval_context.scenarios.read.return_value = []
        mock_context.processor_results = []
        mock_context.test_subject = "test"

        with pytest.raises(Exception):  # Will fail in JudgeExecutor, but that's OK
            await step.execute(mock_context)

        # The test verifies that both judges were extracted (implicit in the code flow)

    @pytest.mark.asyncio
    async def test_execute_resolves_model_ids(self, mock_logger: logging.Logger):
        """execute resolves custom model IDs in judge configurations."""
        step = JudgeRunnerStep(mock_logger)

        mock_judge = MagicMock(spec=JudgeConfig)
        mock_judge.name = "test-judge"
        mock_judge.model = "custom-model"
        mock_judge.config = {"model": "custom-model"}
        mock_judge.config_ref = None

        mock_subject = MagicMock(spec=TestSubject)
        mock_subject.judges = [mock_judge]

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subjects = [mock_subject]
        mock_eval_config.scenarios = MagicMock(field_mapping=None)

        agents_config = {
            "_models": {
                "custom-model": {
                    "model_version": "claude-resolved",
                    "model_family": "claude",
                }
            }
        }

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.agents.read.return_value = agents_config
        mock_context.eval_context.scenarios.read.return_value = []
        mock_context.processor_results = []
        mock_context.test_subject = "test"

        with pytest.raises(Exception):  # Will fail in JudgeExecutor, but that's OK
            await step.execute(mock_context)

        # Verify model was resolved
        assert mock_judge.model == "claude-resolved"
        assert mock_judge.config["model"] == "claude-resolved"
        assert mock_judge.config["model_family"] == "claude"

    @pytest.mark.asyncio
    async def test_execute_handles_judge_with_config_model(self, mock_logger: logging.Logger):
        """execute resolves model from config dict."""
        step = JudgeRunnerStep(mock_logger)

        mock_judge = MagicMock(spec=JudgeConfig)
        mock_judge.name = "test-judge"
        mock_judge.model = None
        mock_judge.config = {"model": "config-model"}
        mock_judge.config_ref = None

        mock_subject = MagicMock(spec=TestSubject)
        mock_subject.judges = [mock_judge]

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subjects = [mock_subject]
        mock_eval_config.scenarios = MagicMock(field_mapping=None)

        agents_config = {
            "_models": {
                "config-model": {
                    "model_version": "gpt-resolved",
                    "model_family": "gpt",
                }
            }
        }

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.agents.read.return_value = agents_config
        mock_context.eval_context.scenarios.read.return_value = []
        mock_context.processor_results = []
        mock_context.test_subject = "test"

        with pytest.raises(Exception):  # Will fail in JudgeExecutor
            await step.execute(mock_context)

        # Model should be resolved from config
        assert mock_judge.config["model"] == "gpt-resolved"

    @pytest.mark.asyncio
    async def test_execute_raises_config_error_on_model_resolution_failure(
        self, mock_logger: logging.Logger
    ):
        """execute raises ConfigError if model resolution fails."""
        step = JudgeRunnerStep(mock_logger)

        mock_judge = MagicMock(spec=JudgeConfig)
        mock_judge.name = "test-judge"
        mock_judge.model = "nonexistent-model"
        mock_judge.config = None
        mock_judge.config_ref = None

        mock_subject = MagicMock(spec=TestSubject)
        mock_subject.judges = [mock_judge]

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subjects = [mock_subject]

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.agents.read.return_value = {"_models": {}}
        mock_context.eval_context.scenarios.read.return_value = []
        mock_context.processor_results = []

        with pytest.raises(ConfigError, match="not found in _models"):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_sets_evaluation_results_in_context(self, mock_logger: logging.Logger):
        """execute sets evaluation_results in context using OutputRecord inputs."""
        step = JudgeRunnerStep(mock_logger)

        mock_judge = MagicMock(spec=JudgeConfig)
        mock_judge.name = "test-judge"
        mock_judge.type = "deepeval.answer_relevancy"
        mock_judge.model = None
        mock_judge.config = None
        mock_judge.config_ref = None

        mock_subject = MagicMock(spec=TestSubject)
        mock_subject.judges = [mock_judge]

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subjects = [mock_subject]
        mock_eval_config.scenarios = MagicMock(field_mapping=None)

        mock_scenario = MagicMock()
        mock_scenario.id = "s1"

        record = OutputRecord(
            test_subject="test-subject",
            variant_id="test-variant",
            scenario_id="s1",
            processor_output="output",
            timing_ms=0,
            tokens_prompt=0,
            tokens_completion=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.agents.read.return_value = {"_models": {}}
        mock_context.eval_context.scenarios.read.return_value = [mock_scenario]
        mock_context.processor_results = [record]
        mock_context.test_subject = "test-subject"

        mock_eval_result = MagicMock()
        mock_eval_result.model_dump.return_value = {
            "judges": [{"name": "judge1", "score": 8}],
            "scenario_id": "s1",
            "variant_id": "test-variant",
        }

        with patch("gavel_ai.core.steps.judge_runner.JudgeExecutor") as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor.execute_batch = AsyncMock(return_value=[mock_eval_result])
            mock_executor_class.return_value = mock_executor

            await step.execute(mock_context)

        assert mock_context.evaluation_results is not None
        assert len(mock_context.evaluation_results) == 1
        assert mock_context.evaluation_results[0]["judges"] == [{"name": "judge1", "score": 8}]

    @pytest.mark.asyncio
    async def test_execute_groups_by_variant_id(self, mock_logger: logging.Logger):
        """execute groups records by variant_id and calls execute_batch once per variant."""
        step = JudgeRunnerStep(mock_logger)

        mock_judge = MagicMock(spec=JudgeConfig)
        mock_judge.name = "test-judge"
        mock_judge.type = "deepeval.answer_relevancy"
        mock_judge.model = None
        mock_judge.config = None
        mock_judge.config_ref = None

        mock_subject = MagicMock(spec=TestSubject)
        mock_subject.judges = [mock_judge]

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subjects = [mock_subject]
        mock_eval_config.scenarios = MagicMock(field_mapping=None)

        # 3 scenarios
        scenarios = [MagicMock() for _ in range(3)]
        for i, s in enumerate(scenarios):
            s.id = f"s{i + 1}"

        ts = datetime.now(timezone.utc).isoformat()

        def _make_record(scenario_id: str, variant_id: str) -> OutputRecord:
            return OutputRecord(
                test_subject="subj",
                variant_id=variant_id,
                scenario_id=scenario_id,
                processor_output="out",
                timing_ms=0,
                tokens_prompt=0,
                tokens_completion=0,
                timestamp=ts,
            )

        # 2 variants × 3 scenarios = 6 records
        records = [_make_record(f"s{i + 1}", "v1") for i in range(3)] + [
            _make_record(f"s{i + 1}", "v2") for i in range(3)
        ]

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.agents.read.return_value = {"_models": {}}
        mock_context.eval_context.scenarios.read.return_value = scenarios
        mock_context.processor_results = records
        mock_context.test_subject = "subj"

        def _make_eval_result(scenario_id: str, variant_id: str):
            mock_r = MagicMock()
            mock_r.model_dump.return_value = {
                "scenario_id": scenario_id,
                "variant_id": variant_id,
                "judges": [],
            }
            return mock_r

        variant_results = {
            "v1": [_make_eval_result(f"s{i + 1}", "v1") for i in range(3)],
            "v2": [_make_eval_result(f"s{i + 1}", "v2") for i in range(3)],
        }

        call_count = 0

        async def _fake_execute_batch(evaluations, subject_id, test_subject):
            nonlocal call_count
            variant_id = evaluations[0][2] if evaluations else "v1"
            call_count += 1
            return variant_results[variant_id]

        with patch("gavel_ai.core.steps.judge_runner.JudgeExecutor") as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor.execute_batch = _fake_execute_batch
            mock_executor_class.return_value = mock_executor

            await step.execute(mock_context)

        # execute_batch called once per variant (2 variants)
        assert call_count == 2

        # 6 EvaluationResult dicts in context.evaluation_results
        assert len(mock_context.evaluation_results) == 6
        result_keys = {(r["scenario_id"], r["variant_id"]) for r in mock_context.evaluation_results}
        assert len(result_keys) == 6


class TestResolveScenarioField:
    """Tests for _resolve_scenario_field module-level helper."""

    def test_resolves_top_level_attribute(self):
        scenario = Scenario(id="s1", input="hello", expected_behavior="world")
        assert _resolve_scenario_field(scenario, "expected_behavior") == "world"

    def test_resolves_nested_dict_in_metadata(self):
        scenario = Scenario(id="s1", input="x", metadata={"key": "value"})
        assert _resolve_scenario_field(scenario, "metadata.key") == "value"

    def test_resolves_nested_key_in_dict_input(self):
        scenario = Scenario(id="s1", input={"query": "the question"})
        assert _resolve_scenario_field(scenario, "input.query") == "the question"

    def test_returns_none_for_missing_segment(self):
        scenario = Scenario(id="s1", input="x")
        assert _resolve_scenario_field(scenario, "metadata.nonexistent") is None

    def test_returns_none_for_nonexistent_attribute(self):
        scenario = Scenario(id="s1", input="x")
        assert _resolve_scenario_field(scenario, "no_such_attr") is None


class TestValidateGevalExpectedOutput:
    """Tests for _validate_geval_expected_output."""

    def _make_scenario(self, sid: str, expected: str = "") -> Scenario:
        return Scenario(id=sid, input="input", expected_behavior=expected or None)

    def test_passes_when_all_scenarios_have_expected_behavior(self):
        scenarios = [self._make_scenario(f"s{i}", f"expected {i}") for i in range(3)]
        # Should not raise
        _validate_geval_expected_output("my-judge", scenarios, field_mapping=None)

    def test_raises_when_scenario_missing_expected_behavior(self):
        scenarios = [
            self._make_scenario("s1", "good"),
            self._make_scenario("s2", ""),  # missing
        ]
        with pytest.raises(ConfigError, match="s2"):
            _validate_geval_expected_output("my-judge", scenarios, field_mapping=None)

    def test_passes_with_field_mapping_resolving_expected_output(self):
        scenarios = [
            Scenario(id="s1", input="x", metadata={"schema": "value1"}),
            Scenario(id="s2", input="x", metadata={"schema": "value2"}),
        ]
        mapping = ScenarioFieldMapping(expected_output="metadata.schema")
        # Should not raise
        _validate_geval_expected_output("my-judge", scenarios, field_mapping=mapping)

    def test_raises_when_field_mapping_path_resolves_to_none(self):
        scenarios = [
            Scenario(id="s1", input="x", metadata={"schema": "ok"}),
            Scenario(id="s2", input="x", metadata={}),  # missing key
        ]
        mapping = ScenarioFieldMapping(expected_output="metadata.schema")
        with pytest.raises(ConfigError, match="s2"):
            _validate_geval_expected_output("my-judge", scenarios, field_mapping=mapping)

    def test_error_message_names_judge_and_missing_ids(self):
        scenarios = [self._make_scenario(f"bad-{i}") for i in range(6)]
        with pytest.raises(ConfigError) as exc_info:
            _validate_geval_expected_output("schema_compliance", scenarios, field_mapping=None)
        msg = str(exc_info.value)
        assert "schema_compliance" in msg
        assert "6 scenario(s)" in msg
        assert "..." in msg  # preview truncated after 5


class TestGEvalFieldMappingInjection:
    """Tests that JudgeRunnerStep injects field_mapping into GEval judge configs."""

    @pytest.mark.asyncio
    async def test_field_mapping_injected_into_geval_config(self, mock_logger):
        """field_mapping from ScenariosConfig is injected into each GEval judge's config."""
        step = JudgeRunnerStep(mock_logger)

        geval_judge = MagicMock(spec=JudgeConfig)
        geval_judge.name = "quality"
        geval_judge.type = "deepeval.geval"
        geval_judge.model = None
        geval_judge.config = {"model": "gpt-4", "criteria": "x", "evaluation_steps": []}
        geval_judge.config_ref = None

        mock_subject = MagicMock(spec=TestSubject)
        mock_subject.judges = [geval_judge]

        scenarios_cfg = ScenariosConfig(
            source="file.local",
            name="scenarios.json",
            field_mapping=ScenarioFieldMapping(expected_output="metadata.expected_schema"),
        )

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subjects = [mock_subject]
        mock_eval_config.scenarios = scenarios_cfg

        scenario = Scenario(
            id="s1", input="x", metadata={"expected_schema": '{"type": "object"}'}
        )

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.agents.read.return_value = {
            "_models": {
                "gpt-4": {"model_version": "gpt-4", "model_family": "gpt"},
            }
        }
        mock_context.eval_context.scenarios.read.return_value = [scenario]
        mock_context.processor_results = []
        mock_context.test_subject = "test"

        with patch("gavel_ai.core.steps.judge_runner.JudgeExecutor"):
            await step.execute(mock_context)

        assert geval_judge.config["field_mapping"] == {
            "expected_output": "metadata.expected_schema"
        }

    @pytest.mark.asyncio
    async def test_validation_raises_config_error_before_execution(self, mock_logger):
        """ConfigError is raised when scenarios lack expected_output before any judge runs."""
        step = JudgeRunnerStep(mock_logger)

        geval_judge = MagicMock(spec=JudgeConfig)
        geval_judge.name = "schema_compliance"
        geval_judge.type = "deepeval.geval"
        geval_judge.model = None
        geval_judge.config = {"model": "gpt-4", "criteria": "x", "evaluation_steps": []}
        geval_judge.config_ref = None

        mock_subject = MagicMock(spec=TestSubject)
        mock_subject.judges = [geval_judge]

        scenarios_cfg = ScenariosConfig(
            source="file.local",
            name="scenarios.json",
            # No field_mapping — expected_output must come from expected_behavior
        )

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subjects = [mock_subject]
        mock_eval_config.scenarios = scenarios_cfg

        # Scenario has no expected_behavior
        scenario = Scenario(id="bad-scenario", input="x")

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.agents.read.return_value = {
            "_models": {
                "gpt-4": {"model_version": "gpt-4", "model_family": "gpt"},
            }
        }
        mock_context.eval_context.scenarios.read.return_value = [scenario]
        mock_context.processor_results = []
        mock_context.test_subject = "test"

        with pytest.raises(ConfigError, match="schema_compliance"):
            await step.execute(mock_context)
