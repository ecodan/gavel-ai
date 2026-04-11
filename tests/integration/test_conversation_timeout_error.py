
import json
import logging
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.steps.conversational_processor import ConversationalProcessingStep
from gavel_ai.processors.turn_generator import GeneratedTurn


class TestConversationTimeoutError:
    """Tests for conversation timeout and error handling."""

    @pytest.fixture
    def setup_eval_env(self, tmp_path: Path):
        eval_root = tmp_path / "evaluations"
        eval_name = "timeout_test_eval"
        eval_dir = eval_root / eval_name

        (eval_dir / "config").mkdir(parents=True)
        (eval_dir / "data").mkdir(parents=True)
        (eval_dir / "runs").mkdir(parents=True)

        eval_config = {
            "eval_name": "timeout_test_eval",
            "eval_type": "conversational",
            "workflow_type": "conversational",
            "test_subject_type": "local",
            "test_subjects": [{"prompt_name": "default", "judges": []}],
            "conversational": {
                "max_turns": 2,
                "max_duration_ms": 30000,
                "turn_generator": {"model_id": "gpt-4", "temperature": 0.0},
                "retry_config": {
                    "max_retries": 1,
                    "initial_delay_ms": 100,
                    "max_delay_ms": 1000,
                    "backoff_factor": 2.0
                }
            },
            "variants": ["v1"],
            "execution": {"max_concurrent": 1},
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
        }
        with open(eval_dir / "config" / "eval_config.json", "w") as f:
            json.dump(eval_config, f)

        agents_config = {
            "_models": {
                "gpt-4": {
                    "model_provider": "openai",
                    "model_family": "gpt",
                    "model_version": "gpt-4",
                    "model_parameters": {"temperature": 0.0},
                    "provider_auth": {"api_key": "test_key"},
                }
            },
            "v1": {"model_id": "gpt-4", "prompt": "default:v1"},
        }
        with open(eval_dir / "config" / "agents.json", "w") as f:
            json.dump(agents_config, f)

        scenarios = [
            {"scenario_id": "s1", "input": "Goal 1"}
        ]
        with open(eval_dir / "data" / "scenarios.json", "w") as f:
            json.dump(scenarios, f)

        return eval_name, eval_root

    @pytest.mark.asyncio
    async def test_max_turns_enforcement(self, setup_eval_env):
        eval_name, eval_root = setup_eval_env
        eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root)
        run_ctx = LocalRunContext(eval_ctx, base_dir=eval_ctx.eval_dir / "runs")
        
        step = ConversationalProcessingStep(logging.getLogger("test"))
        
        with patch("gavel_ai.core.steps.conversational_processor.TurnGenerator") as MockTurnGen:
            mock_turn_gen = MagicMock()
            MockTurnGen.return_value = mock_turn_gen
            
            async def mock_generate(*args, **kwargs):
                return GeneratedTurn(content="Continuing...", should_continue=True, metadata={})
                
            mock_turn_gen.generate_turn.side_effect = mock_generate
            
            with patch("gavel_ai.providers.factory.ProviderFactory.call_agent") as mock_call:
                mock_call.return_value = MagicMock(output="AI response", metadata={})
                
                await step.execute(run_ctx)
                
        results = run_ctx.conversation_results[0]
        assert len(results.conversation_transcript.turns) == 5
        assert results.completed is True

    @pytest.mark.asyncio
    async def test_max_duration_enforcement(self, setup_eval_env):
        eval_name, eval_root = setup_eval_env
        eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root)
        run_ctx = LocalRunContext(eval_ctx, base_dir=eval_ctx.eval_dir / "runs")
        
        step = ConversationalProcessingStep(logging.getLogger("test"))
        
        with patch("gavel_ai.core.steps.conversational_processor.TurnGenerator") as MockTurnGen:
            mock_turn_gen = MagicMock()
            MockTurnGen.return_value = mock_turn_gen
            
            async def mock_generate(*args, **kwargs):
                return GeneratedTurn(content="Too slow", should_continue=True, metadata={})
                
            mock_turn_gen.generate_turn.side_effect = mock_generate
            
            with patch("gavel_ai.providers.factory.ProviderFactory.call_agent") as mock_call:
                mock_call.return_value = MagicMock(output="AI response", metadata={})
                
                with patch("time.time") as mock_time:
                    # Logic needs enough timestamps to pass through loop initialization and checks
                    # 1000.0: start_time
                    # 50000.0: first loop check (exceeds 30000ms)
                    mock_time.side_effect = [1000.0, 1000.1, 1040.0, 50000.0, 50100.0, 50200.0]
                    await step.execute(run_ctx)
                
        results = run_ctx.conversation_results[0]
        assert len(results.conversation_transcript.turns) == 2
        assert results.completed is False

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, setup_eval_env):
        eval_name, eval_root = setup_eval_env
        eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root)
        run_ctx = LocalRunContext(eval_ctx, base_dir=eval_ctx.eval_dir / "runs")
        
        step = ConversationalProcessingStep(logging.getLogger("test"))
        
        with patch("gavel_ai.core.steps.conversational_processor.TurnGenerator") as MockTurnGen:
            mock_turn_gen = MagicMock()
            MockTurnGen.return_value = mock_turn_gen
            
            async def mock_gen(*args, **kwargs):
                if not hasattr(mock_gen, "idx"): mock_gen.idx = 0
                res = [
                    GeneratedTurn(content="Hi", should_continue=True, metadata={}),
                    GeneratedTurn(content="Bye", should_continue=False, metadata={})
                ][mock_gen.idx]
                mock_gen.idx += 1
                return res
            mock_turn_gen.generate_turn.side_effect = mock_gen
            
            with patch("gavel_ai.providers.factory.ProviderFactory.call_agent") as mock_call:
                # First call fails with transient error, second succeeds
                mock_call.side_effect = [
                    asyncio.TimeoutError("Timeout"),
                    MagicMock(output="AI response recovered", metadata={})
                ]
                
                await step.execute(run_ctx)
                
        results = run_ctx.conversation_results[0]
        assert results.error is None
        assert len(results.conversation_transcript.turns) == 2
        assert results.conversation_transcript.turns[1].content == "AI response recovered"

    @pytest.mark.asyncio
    async def test_permanent_failure(self, setup_eval_env):
        eval_name, eval_root = setup_eval_env
        eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root)
        run_ctx = LocalRunContext(eval_ctx, base_dir=eval_ctx.eval_dir / "runs")
        
        step = ConversationalProcessingStep(logging.getLogger("test"))
        
        with patch("gavel_ai.core.steps.conversational_processor.TurnGenerator") as MockTurnGen:
            mock_turn_gen = MagicMock()
            MockTurnGen.return_value = mock_turn_gen
            
            async def mock_gen(*args, **kwargs):
                return GeneratedTurn(content="Hi", should_continue=True, metadata={})
            mock_turn_gen.generate_turn.side_effect = mock_gen
            
            with patch("gavel_ai.providers.factory.ProviderFactory.call_agent") as mock_call:
                # Permanent failure
                mock_call.side_effect = ValueError("401 Unauthorized")
                
                await step.execute(run_ctx)
                
        results = run_ctx.conversation_results[0]
        assert results.error is not None
        assert "auth_error" in str(results.error).lower() or "401" in str(results.error)
        assert mock_call.call_count == 1
        
        # Verify results_raw has the error
        assert len(run_ctx.results_raw.read()) == 1
        assert run_ctx.results_raw.read()[0].error is not None
        assert run_ctx.results_raw.read()[0].metadata["error_type"] == "auth_error"

    @pytest.mark.asyncio
    async def test_turn_generator_failure(self, setup_eval_env):
        eval_name, eval_root = setup_eval_env
        eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root)
        run_ctx = LocalRunContext(eval_ctx, base_dir=eval_ctx.eval_dir / "runs")
        
        step = ConversationalProcessingStep(logging.getLogger("test"))
        
        from gavel_ai.conversational.errors import TurnGenerationError
        
        with patch("gavel_ai.core.steps.conversational_processor.TurnGenerator") as MockTurnGen:
            mock_turn_gen = MagicMock()
            MockTurnGen.return_value = mock_turn_gen
            
            # Initial turn generation fails
            async def mock_gen_fail(*args, **kwargs):
                raise TurnGenerationError("Failed to generate turn")
                
            mock_turn_gen.generate_turn.side_effect = mock_gen_fail
            
            await step.execute(run_ctx)
            
        results = run_ctx.conversation_results[0]
        assert results.error is not None
        assert "turn_generation" in results.error or "Failed to generate turn" in results.error
        assert results.completed is False
        assert len(results.conversation_transcript.turns) == 0
        
        # Verify results_raw has the error (THIS IS NEW)
        assert len(run_ctx.results_raw.read()) == 1
        assert run_ctx.results_raw.read()[0].error is not None
        assert run_ctx.results_raw.read()[0].metadata["turn_number"] == 0
        assert run_ctx.results_raw.read()[0].metadata["error_type"] == "turn_generation"
