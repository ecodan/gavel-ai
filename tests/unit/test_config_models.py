import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for config models.
"""

import pytest
from pydantic import ValidationError

from gavel_ai.models.config import (
    AgentConfig,
    AsyncConfig,
    ConversationalConfig,
    ElaborationConfig,
    EvalConfig,
    ExecutionConfig,
    GEvalConfig,
    JudgeConfig,
    ScenariosConfig,
    TestSubject,
    TurnGeneratorConfig,
)


class TestJudgeConfig:
    """Test JudgeConfig model."""

    def test_judge_config_basic_creation(self):
        """JudgeConfig can be created with required fields."""
        judge = JudgeConfig(
            name="similarity",
            type="deepeval.similarity",
        )
        assert judge.name == "similarity"
        assert judge.type == "deepeval.similarity"
        assert judge.config is None
        assert judge.config_ref is None
        assert judge.threshold is None
        assert judge.model is None

    def test_judge_config_all_fields(self):
        """JudgeConfig can include all optional fields."""
        judge = JudgeConfig(
            name="custom",
            type="custom.my_judge",
            config={"param1": "value1", "param2": 42},
            config_ref="/path/to/config.json",
            threshold=0.8,
            model="claude-4-5-sonnet",
        )
        assert judge.config["param1"] == "value1"
        assert judge.config_ref == "/path/to/config.json"
        assert judge.threshold == 0.8
        assert judge.model == "claude-4-5-sonnet"

    def test_judge_config_with_geval_fields(self):
        """JudgeConfig can include GEval-specific fields."""
        judge = JudgeConfig(
            name="geval_accuracy",
            type="geval.accuracy",
            criteria="The response must accurately answer question",
            evaluation_steps=[
                "Step 1: Check if answer is factually correct",
                "Step 2: Check if answer is complete",
            ],
        )
        assert judge.criteria == "The response must accurately answer question"
        assert len(judge.evaluation_steps) == 2

    def test_judge_config_extra_ignore(self):
        """JudgeConfig ignores extra fields."""
        judge_dict = {
            "name": "test",
            "type": "test.type",
            "extra_field": "ignored",
        }
        judge = JudgeConfig(**judge_dict)
        assert not hasattr(judge, "extra_field")

    def test_judge_config_requires_name(self):
        """JudgeConfig requires name field."""
        with pytest.raises(ValidationError):
            JudgeConfig(type="test.type")

    def test_judge_config_requires_type(self):
        """JudgeConfig requires type field."""
        with pytest.raises(ValidationError):
            JudgeConfig(name="test")


class TestScenariosConfig:
    """Test ScenariosConfig model."""

    def test_scenarios_config_basic_creation(self):
        """ScenariosConfig can be created with required fields."""
        config = ScenariosConfig(
            source="file.local",
            name="scenarios.json",
        )
        assert config.source == "file.local"
        assert config.name == "scenarios.json"

    def test_scenarios_config_extra_ignore(self):
        """ScenariosConfig ignores extra fields."""
        config_dict = {
            "source": "file.local",
            "name": "scenarios.json",
            "extra_field": "ignored",
        }
        config = ScenariosConfig(**config_dict)
        assert not hasattr(config, "extra_field")

    def test_scenarios_config_requires_source(self):
        """ScenariosConfig requires source field."""
        with pytest.raises(ValidationError):
            ScenariosConfig(name="scenarios.json")

    def test_scenarios_config_requires_name(self):
        """ScenariosConfig requires name field."""
        with pytest.raises(ValidationError):
            ScenariosConfig(source="file.local")


class TestExecutionConfig:
    """Test ExecutionConfig model."""

    def test_execution_config_default_values(self):
        """ExecutionConfig has sensible default values."""
        config = ExecutionConfig()
        assert config.max_concurrent == 5

    def test_execution_config_custom_max_concurrent(self):
        """ExecutionConfig can customize max_concurrent."""
        config = ExecutionConfig(max_concurrent=10)
        assert config.max_concurrent == 10

    def test_execution_config_extra_ignore(self):
        """ExecutionConfig ignores extra fields."""
        config_dict = {"max_concurrent": 5, "extra_field": "ignored"}
        config = ExecutionConfig(**config_dict)
        assert not hasattr(config, "extra_field")


class TestAsyncConfig:
    """Test AsyncConfig model."""

    def test_async_config_default_values(self):
        """AsyncConfig has sensible default values."""
        config = AsyncConfig()
        assert config.num_workers == 8
        assert config.arrival_rate_per_sec == 20.0
        assert config.exec_rate_per_min == 100
        assert config.max_retries == 3
        assert config.task_timeout_seconds == 300
        assert config.stuck_timeout_seconds == 600
        assert config.emit_progress_interval_sec == 10

    def test_async_config_custom_values(self):
        """AsyncConfig can customize all fields."""
        config = AsyncConfig(
            num_workers=16,
            arrival_rate_per_sec=50.0,
            exec_rate_per_min=500,
            max_retries=5,
            task_timeout_seconds=600,
            stuck_timeout_seconds=1200,
            emit_progress_interval_sec=20,
        )
        assert config.num_workers == 16
        assert config.arrival_rate_per_sec == 50.0
        assert config.exec_rate_per_min == 500
        assert config.max_retries == 5
        assert config.task_timeout_seconds == 600
        assert config.stuck_timeout_seconds == 1200
        assert config.emit_progress_interval_sec == 20

    def test_async_config_extra_ignore(self):
        """AsyncConfig ignores extra fields."""
        config_dict = {"num_workers": 8, "extra_field": "ignored"}
        config = AsyncConfig(**config_dict)
        assert not hasattr(config, "extra_field")


class TestTestSubject:
    """Test TestSubject model."""

    def test_test_subject_basic_creation(self):
        """TestSubject can be created with required fields."""
        subject = TestSubject(
            judges=[
                JudgeConfig(name="similarity", type="deepeval.similarity"),
            ],
        )
        assert subject.judges is not None
        assert len(subject.judges) == 1
        assert subject.prompt_name is None

    def test_test_subject_with_prompt_name(self):
        """TestSubject can include prompt_name."""
        subject = TestSubject(
            prompt_name="default_prompt",
            judges=[
                JudgeConfig(name="similarity", type="deepeval.similarity"),
            ],
        )
        assert subject.prompt_name == "default_prompt"

    def test_test_subject_multiple_judges(self):
        """TestSubject can include multiple judges."""
        subject = TestSubject(
            prompt_name="prompt",
            judges=[
                JudgeConfig(name="similarity", type="deepeval.similarity"),
                JudgeConfig(name="accuracy", type="geval.accuracy"),
            ],
        )
        assert len(subject.judges) == 2

    def test_test_subject_with_remote_config(self):
        """TestSubject can include remote system configuration."""
        subject = TestSubject(
            system_id="remote-system-1",
            protocol="acp",
            config={"url": "https://api.example.com", "timeout": 30},
            judges=[
                JudgeConfig(name="similarity", type="deepeval.similarity"),
            ],
        )
        assert subject.system_id == "remote-system-1"
        assert subject.protocol == "acp"
        assert subject.config["url"] == "https://api.example.com"

    def test_test_subject_extra_ignore(self):
        """TestSubject ignores extra fields."""
        subject_dict = {
            "judges": [JudgeConfig(name="test", type="test.type")],
            "extra_field": "ignored",
        }
        subject = TestSubject(**subject_dict)
        assert not hasattr(subject, "extra_field")

    def test_test_subject_requires_judges(self):
        """TestSubject requires judges field."""
        with pytest.raises(ValidationError):
            TestSubject()


class TestGEvalConfig:
    """Test GEvalConfig model."""

    def test_geval_config_basic_creation(self):
        """GEvalConfig can be created with required fields."""
        config = GEvalConfig(
            criteria="The response must be accurate",
            evaluation_steps=["Step 1", "Step 2"],
            model="claude-4-5-sonnet",
        )
        assert config.criteria == "The response must be accurate"
        assert len(config.evaluation_steps) == 2
        assert config.model == "claude-4-5-sonnet"
        assert config.threshold == 0.7

    def test_geval_config_custom_threshold(self):
        """GEvalConfig can customize threshold."""
        config = GEvalConfig(
            criteria="Test",
            evaluation_steps=["Step"],
            model="model",
            threshold=0.9,
        )
        assert config.threshold == 0.9

    def test_geval_config_threshold_bounds(self):
        """GEvalConfig enforces threshold bounds (0.0-1.0)."""
        with pytest.raises(ValidationError):
            GEvalConfig(
                criteria="Test",
                evaluation_steps=["Step"],
                model="model",
                threshold=1.5,
            )

        with pytest.raises(ValidationError):
            GEvalConfig(
                criteria="Test",
                evaluation_steps=["Step"],
                model="model",
                threshold=-0.1,
            )

    def test_geval_config_extra_ignore(self):
        """GEvalConfig ignores extra fields."""
        config_dict = {
            "criteria": "Test",
            "evaluation_steps": ["Step"],
            "model": "model",
            "extra_field": "ignored",
        }
        config = GEvalConfig(**config_dict)
        assert not hasattr(config, "extra_field")

    def test_geval_config_requires_criteria(self):
        """GEvalConfig requires criteria field."""
        with pytest.raises(ValidationError):
            GEvalConfig(evaluation_steps=["Step"], model="model")

    def test_geval_config_requires_evaluation_steps(self):
        """GEvalConfig requires evaluation_steps field."""
        with pytest.raises(ValidationError):
            GEvalConfig(criteria="Test", model="model")

    def test_geval_config_requires_model(self):
        """GEvalConfig requires model field."""
        with pytest.raises(ValidationError):
            GEvalConfig(criteria="Test", evaluation_steps=["Step"])


class TestEvalConfig:
    """Test EvalConfig model."""

    def test_eval_config_basic_creation(self):
        """EvalConfig can be created with required fields."""
        config = EvalConfig(
            eval_type="oneshot",
            eval_name="test-eval",
            test_subject_type="local",
            test_subjects=[
                TestSubject(
                    prompt_name="prompt",
                    judges=[JudgeConfig(name="test", type="test.type")],
                ),
            ],
            variants=["variant1", "variant2"],
            scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
        )
        assert config.eval_type == "oneshot"
        assert config.eval_name == "test-eval"
        assert len(config.variants) == 2
        assert config.description is None

    def test_eval_config_all_fields(self):
        """EvalConfig can include all optional fields."""
        config = EvalConfig(
            eval_type="oneshot",
            eval_name="test-eval",
            description="Test evaluation",
            test_subject_type="local",
            test_subjects=[
                TestSubject(
                    prompt_name="prompt",
                    judges=[JudgeConfig(name="test", type="test.type")],
                ),
            ],
            variants=["v1", "v2"],
            scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
            execution=ExecutionConfig(max_concurrent=10),
            async_config=AsyncConfig(num_workers=16),
        )
        assert config.description == "Test evaluation"
        assert config.execution.max_concurrent == 10
        assert config.async_config.num_workers == 16

    def test_eval_config_extra_ignore(self):
        """EvalConfig ignores extra fields."""
        config_dict = {
            "eval_type": "oneshot",
            "eval_name": "test-eval",
            "test_subject_type": "local",
            "test_subjects": [
                TestSubject(
                    prompt_name="prompt",
                    judges=[JudgeConfig(name="test", type="test.type")],
                ),
            ],
            "variants": ["v1"],
            "scenarios": ScenariosConfig(source="file.local", name="scenarios.json"),
            "extra_field": "ignored",
        }
        config = EvalConfig(**config_dict)
        assert not hasattr(config, "extra_field")

    def test_eval_config_requires_eval_type(self):
        """EvalConfig requires eval_type field."""
        with pytest.raises(ValidationError):
            EvalConfig(
                eval_name="test",
                test_subject_type="local",
                test_subjects=[
                    TestSubject(
                        prompt_name="prompt",
                        judges=[JudgeConfig(name="test", type="test.type")],
                    ),
                ],
                variants=["v1"],
                scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
            )

    def test_eval_config_requires_eval_name(self):
        """EvalConfig requires eval_name field."""
        with pytest.raises(ValidationError):
            EvalConfig(
                eval_type="oneshot",
                test_subject_type="local",
                test_subjects=[
                    TestSubject(
                        prompt_name="prompt",
                        judges=[JudgeConfig(name="test", type="test.type")],
                    ),
                ],
                variants=["v1"],
                scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
            )


class TestAgentConfig:
    """Test AgentConfig in config.py (different from models.agents)."""

    def test_agent_config_basic_creation(self):
        """AgentConfig can be created with required fields."""
        config = AgentConfig(
            model_id="claude-standard",
            prompt="assistant:v1",
        )
        assert config.model_id == "claude-standard"
        assert config.prompt == "assistant:v1"
        assert config.model_parameters is None
        assert config.custom_configs is None

    def test_agent_config_with_optional_fields(self):
        """AgentConfig can include optional fields."""
        config = AgentConfig(
            model_id="claude-standard",
            prompt="assistant:v1",
            model_parameters={"temperature": 0.5},
            custom_configs={"logging": {"enabled": True}},
        )
        assert config.model_parameters is not None
        assert config.custom_configs is not None

    def test_agent_config_extra_ignore(self):
        """AgentConfig ignores extra fields."""
        config_dict = {
            "model_id": "claude-standard",
            "prompt": "assistant:v1",
            "extra_field": "ignored",
        }
        config = AgentConfig(**config_dict)
        assert not hasattr(config, "extra_field")

    def test_agent_config_requires_model_id(self):
        """AgentConfig requires model_id field."""
        with pytest.raises(ValidationError):
            AgentConfig(prompt="v1")

    def test_agent_config_requires_prompt(self):
        """AgentConfig requires prompt field."""
        with pytest.raises(ValidationError):
            AgentConfig(model_id="claude-standard")


class TestTurnGeneratorConfig:
    """Test TurnGeneratorConfig model."""

    def test_turn_generator_config_basic_creation(self):
        """TurnGeneratorConfig can be created with required fields."""
        config = TurnGeneratorConfig(
            model_id="claude-standard",
        )
        assert config.model_id == "claude-standard"
        assert config.temperature == 0.0
        assert config.max_tokens == 500

    def test_turn_generator_config_custom_values(self):
        """TurnGeneratorConfig can customize all fields."""
        from gavel_ai.models.config import TurnGeneratorConfig

        config = TurnGeneratorConfig(
            model_id="gpt-4",
            temperature=0.7,
            max_tokens=1000,
        )
        assert config.model_id == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000

    def test_turn_generator_config_temperature_validation(self):
        """TurnGeneratorConfig validates temperature range (0.0-2.0)."""
        from gavel_ai.models.config import TurnGeneratorConfig

        # Valid temperatures
        TurnGeneratorConfig(model_id="test", temperature=0.0)
        TurnGeneratorConfig(model_id="test", temperature=1.0)
        TurnGeneratorConfig(model_id="test", temperature=2.0)

        # Invalid temperatures
        with pytest.raises(ValidationError):
            TurnGeneratorConfig(model_id="test", temperature=-0.1)

        with pytest.raises(ValidationError):
            TurnGeneratorConfig(model_id="test", temperature=2.1)

    def test_turn_generator_config_max_tokens_validation(self):
        """TurnGeneratorConfig validates max_tokens range (1-4000)."""
        from gavel_ai.models.config import TurnGeneratorConfig

        # Valid values
        TurnGeneratorConfig(model_id="test", max_tokens=1)
        TurnGeneratorConfig(model_id="test", max_tokens=4000)

        # Invalid values
        with pytest.raises(ValidationError):
            TurnGeneratorConfig(model_id="test", max_tokens=0)

        with pytest.raises(ValidationError):
            TurnGeneratorConfig(model_id="test", max_tokens=4001)

    def test_turn_generator_config_extra_ignore(self):
        """TurnGeneratorConfig ignores extra fields."""
        from gavel_ai.models.config import TurnGeneratorConfig

        config_dict = {
            "model_id": "claude-standard",
            "extra_field": "ignored",
        }
        config = TurnGeneratorConfig(**config_dict)
        assert not hasattr(config, "extra_field")

    def test_turn_generator_config_requires_model_id(self):
        """TurnGeneratorConfig requires model_id field."""
        from gavel_ai.models.config import TurnGeneratorConfig

        with pytest.raises(ValidationError):
            TurnGeneratorConfig()


class TestElaborationConfig:
    """Test ElaborationConfig model."""

    def test_elaboration_config_basic_creation(self):
        """ElaborationConfig can be created with default values."""

        config = ElaborationConfig()
        assert config.enabled is False
        assert config.elaboration_template is None
        assert config.model_id is None

    def test_elaboration_config_all_fields(self):
        """ElaborationConfig can include all fields."""

        config = ElaborationConfig(
            enabled=True,
            elaboration_template="prompts/elaborate_scenarios.toml",
            model_id="claude-creative",
        )
        assert config.enabled is True
        assert config.elaboration_template == "prompts/elaborate_scenarios.toml"
        assert config.model_id == "claude-creative"

    def test_elaboration_config_extra_ignore(self):
        """ElaborationConfig ignores extra fields."""

        config_dict = {
            "enabled": True,
            "extra_field": "ignored",
        }
        config = ElaborationConfig(**config_dict)
        assert not hasattr(config, "extra_field")


class TestConversationalConfig:
    """Test ConversationalConfig model."""

    def test_conversational_config_basic_creation(self):
        """ConversationalConfig can be created with required fields."""
        from gavel_ai.models.config import ConversationalConfig, TurnGeneratorConfig

        config = ConversationalConfig(
            turn_generator=TurnGeneratorConfig(model_id="claude-standard"),
        )
        assert config.max_turns == 10
        assert config.max_turn_length == 2000
        assert config.max_duration_ms == 300000
        assert config.elaboration is None
        assert config.turn_generator.model_id == "claude-standard"

    def test_conversational_config_all_fields(self):
        """ConversationalConfig can include all fields."""
        from gavel_ai.models.config import (
            ConversationalConfig,
            TurnGeneratorConfig,
        )

        config = ConversationalConfig(
            max_turns=15,
            max_turn_length=3000,
            turn_generator=TurnGeneratorConfig(model_id="gpt-4", temperature=0.7),
            elaboration=ElaborationConfig(enabled=True, elaboration_template="template.toml"),
            max_duration_ms=600000,
        )
        assert config.max_turns == 15
        assert config.max_turn_length == 3000
        assert config.turn_generator.model_id == "gpt-4"
        assert config.turn_generator.temperature == 0.7
        assert config.elaboration.enabled is True
        assert config.max_duration_ms == 600000

    def test_conversational_config_max_turns_validation(self):
        """ConversationalConfig validates max_turns range (1-100)."""
        from gavel_ai.models.config import ConversationalConfig, TurnGeneratorConfig

        turn_gen = TurnGeneratorConfig(model_id="test")

        # Valid values
        ConversationalConfig(turn_generator=turn_gen, max_turns=1)
        ConversationalConfig(turn_generator=turn_gen, max_turns=100)

        # Invalid values
        with pytest.raises(ValidationError):
            ConversationalConfig(turn_generator=turn_gen, max_turns=0)

        with pytest.raises(ValidationError):
            ConversationalConfig(turn_generator=turn_gen, max_turns=101)

    def test_conversational_config_max_turn_length_validation(self):
        """ConversationalConfig validates max_turn_length range (100-10000)."""
        from gavel_ai.models.config import ConversationalConfig, TurnGeneratorConfig

        turn_gen = TurnGeneratorConfig(model_id="test")

        # Valid values
        ConversationalConfig(turn_generator=turn_gen, max_turn_length=100)
        ConversationalConfig(turn_generator=turn_gen, max_turn_length=10000)

        # Invalid values
        with pytest.raises(ValidationError):
            ConversationalConfig(turn_generator=turn_gen, max_turn_length=99)

        with pytest.raises(ValidationError):
            ConversationalConfig(turn_generator=turn_gen, max_turn_length=10001)

    def test_conversational_config_timeout_validation(self):
        """ConversationalConfig validates max_duration_ms range (30000-3600000)."""
        from gavel_ai.models.config import ConversationalConfig, TurnGeneratorConfig

        turn_gen = TurnGeneratorConfig(model_id="test")

        # Valid values
        ConversationalConfig(turn_generator=turn_gen, max_duration_ms=30000)
        ConversationalConfig(turn_generator=turn_gen, max_duration_ms=3600000)

        # Invalid values
        with pytest.raises(ValidationError):
            ConversationalConfig(turn_generator=turn_gen, max_duration_ms=29999)

        with pytest.raises(ValidationError):
            ConversationalConfig(turn_generator=turn_gen, max_duration_ms=3600001)

    def test_conversational_config_extra_ignore(self):
        """ConversationalConfig ignores extra fields."""
        from gavel_ai.models.config import ConversationalConfig

        config_dict = {
            "turn_generator": {"model_id": "claude-standard"},
            "extra_field": "ignored",
        }
        config = ConversationalConfig(**config_dict)
        assert not hasattr(config, "extra_field")

    def test_conversational_config_requires_turn_generator(self):
        """ConversationalConfig requires turn_generator field."""
        from gavel_ai.models.config import ConversationalConfig

        with pytest.raises(ValidationError):
            ConversationalConfig()


class TestEvalConfigConversationalExtension:
    """Test EvalConfig conversational extensions."""

    def test_eval_config_with_workflow_type_conversational(self):
        """EvalConfig supports workflow_type='conversational'."""
        from gavel_ai.models.config import EvalConfig

        config = EvalConfig(
            eval_type="conversational",  # This will be updated to workflow_type
            eval_name="test-conversational",
            test_subject_type="local",
            test_subjects=[
                TestSubject(
                    judges=[JudgeConfig(name="test", type="test.type")],
                ),
            ],
            variants=["variant1"],
            scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
        )
        # This will need to be updated when we modify EvalConfig
        assert config.eval_type == "conversational"

    def test_eval_config_conversational_validation(self):
        """EvalConfig validates conversational config when workflow_type='conversational'."""
        # Should pass when workflow_type is oneshot without conversational config
        config = EvalConfig(
            workflow_type="oneshot",
            eval_type="oneshot",
            eval_name="test-oneshot",
            test_subject_type="local",
            test_subjects=[
                TestSubject(
                    judges=[JudgeConfig(name="test", type="test.type")],
                ),
            ],
            variants=["variant1"],
            scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
        )
        assert config.workflow_type == "oneshot"
        assert config.conversational is None

        # Should pass when workflow_type is conversational with conversational config
        config = EvalConfig(
            workflow_type="conversational",
            eval_type="conversational",
            eval_name="test-conversational",
            test_subject_type="local",
            test_subjects=[
                TestSubject(
                    judges=[JudgeConfig(name="test", type="test.type")],
                ),
            ],
            variants=["variant1"],
            scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
            conversational=ConversationalConfig(
                turn_generator=TurnGeneratorConfig(model_id="claude-standard")
            ),
        )
        assert config.workflow_type == "conversational"
        assert config.conversational is not None
        assert config.conversational.turn_generator.model_id == "claude-standard"

        # Should fail when workflow_type is conversational but no conversational config
        with pytest.raises(ValueError) as excinfo:
            EvalConfig(
                workflow_type="conversational",
                eval_type="conversational",
                eval_name="test-conversational",
                test_subject_type="local",
                test_subjects=[
                    TestSubject(
                        judges=[JudgeConfig(name="test", type="test.type")],
                    ),
                ],
                variants=["variant1"],
                scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
                # Missing conversational config
            )
        assert "conversational config is required when workflow_type='conversational'" in str(
            excinfo.value
        )

    def test_eval_config_load_conversational_from_json(self):
        """EvalConfig can load conversational config from JSON file."""
        import json
        import os
        import tempfile

        # Create a conversational config JSON
        config_dict = {
            "workflow_type": "conversational",
            "eval_type": "conversational",
            "eval_name": "test-conversational",
            "test_subject_type": "local",
            "test_subjects": [
                {"judges": [{"name": "relevancy", "type": "deepeval.turn_relevancy"}]}
            ],
            "variants": ["variant1"],
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
            "conversational": {
                "max_turns": 15,
                "max_turn_length": 3000,
                "turn_generator": {
                    "model_id": "claude-standard",
                    "temperature": 0.0,
                    "max_tokens": 500,
                },
                "elaboration": {"enabled": True, "elaboration_template": "prompts/elaborate.toml"},
                "max_duration_ms": 600000,
            },
        }

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_dict, f)
            temp_file = f.name

        try:
            # Load and validate the config
            with open(temp_file) as f:
                loaded_config = json.load(f)

            config = EvalConfig.model_validate(loaded_config)

            # Verify all fields loaded correctly
            assert config.workflow_type == "conversational"
            assert config.eval_name == "test-conversational"
            assert config.conversational is not None
            assert config.conversational.max_turns == 15
            assert config.conversational.max_turn_length == 3000
            assert config.conversational.turn_generator.model_id == "claude-standard"
            assert config.conversational.turn_generator.temperature == 0.0
            assert config.conversational.turn_generator.max_tokens == 500
            assert config.conversational.elaboration.enabled is True
            assert (
                config.conversational.elaboration.elaboration_template == "prompts/elaborate.toml"
            )
            assert config.conversational.max_duration_ms == 600000

        finally:
            # Clean up temporary file
            os.unlink(temp_file)
