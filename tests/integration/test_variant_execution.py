"""
Integration tests for multi-variant conversational execution.

Verifies that ConversationalProcessingStep correctly handles:
1. Multiple variants executing in parallel
2. Deterministic user turns across variants
3. Result persistence to results_raw.jsonl and conversations.jsonl
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.steps import ConversationalProcessingStep
from gavel_ai.models.runtime import OutputRecord


class TestVariantExecutionIntegration:
    """Integration tests for multi-variant execution."""

    @pytest.fixture
    def setup_eval_environment(self, tmp_path: Path):
        """Setup a temporary evaluation environment with configs."""
        eval_root = tmp_path / "evaluations"
        eval_name = "variant_test_eval"
        eval_dir = eval_root / eval_name
        
        # Create directory structure
        (eval_dir / "config").mkdir(parents=True)
        (eval_dir / "data").mkdir(parents=True)
        (eval_dir / "runs").mkdir(parents=True)

        # 1. eval_config.json
        eval_config = {
            "eval_name": "variant_test_eval",
            "eval_type": "conversational",
            "workflow_type": "conversational",
            "test_subject_type": "local",
            "test_subjects": [
                {
                    "prompt_name": "default",
                    "judges": []
                }
            ],
            "conversational": {
                "max_turns": 3,
                "turn_generator": {
                    "model_id": "gpt-4",
                    "temperature": 0.0
                }
            },
            "variants": ["variant-1", "variant-2"],
            "execution": {"max_concurrent": 2},
            "scenarios": {
                "source": "file.local",
                "name": "scenarios.json"
            }
        }
        with open(eval_dir / "config" / "eval_config.json", "w") as f:
            json.dump(eval_config, f)

        # 2. agents.json
        agents_config = {
            "_models": {
                "gpt-4": {
                    "model_provider": "openai",
                    "model_family": "gpt",
                    "model_version": "gpt-4",
                    "model_parameters": {"temperature": 0.0},
                    "provider_auth": {"api_key": "test_key"}
                },
                "claude-3": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-3-sonnet",
                    "model_parameters": {"temperature": 0.0},
                    "provider_auth": {"api_key": "test_key"}
                }
            },
            "variant-1": {"model_id": "gpt-4", "prompt": "default:v1"},
            "variant-2": {"model_id": "claude-3", "prompt": "default:v1"}
        }
        with open(eval_dir / "config" / "agents.json", "w") as f:
            json.dump(agents_config, f)

        # 3. scenarios.json
        scenarios = [
            {
                "scenario_id": "s1",
                "input": "Book a flight to Paris",
                "metadata": {
                    "context": "User is flexible with dates",
                    "user_goal": "Book a flight to Paris"
                }
            }
        ]
        with open(eval_dir / "data" / "scenarios.json", "w") as f:
            json.dump(scenarios, f)

        return eval_name, eval_root

    @pytest.mark.asyncio
    async def test_multi_variant_execution_flow(self, setup_eval_environment):
        """
        Verify complete execution flow with multiple variants.
        
        - Loads config from filesystem
        - Executes both variants
        - Verifies distinct results are written to disk
        """
        eval_name, eval_root = setup_eval_environment
        
        # Initialize contexts
        eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root)
        run_ctx = LocalRunContext(eval_ctx)
        
        # Instantiate step
        logger = logging.getLogger("test_integration")
        step = ConversationalProcessingStep(logger)
        
        # Mock TurnGenerator to be deterministic but realistic
        # We mock at the class level to avoid complex LLM mocking in TurnGenerator
        with patch("gavel_ai.core.steps.conversational_processor.TurnGenerator") as MockTurnGen:
            mock_turn_gen_instance = MagicMock()
            MockTurnGen.return_value = mock_turn_gen_instance
            
            # Setup turn sequence: 
            # 1. User says "Hi" -> Continue
            # 2. User says "Book Paris" -> Stop
            from gavel_ai.processors.turn_generator import GeneratedTurn
            
            # Use AsyncMock for the method itself
            mock_generate = MagicMock()
            async def side_effect(*args, **kwargs):
                return mock_generate(*args, **kwargs)
                
            mock_turn_gen_instance.generate_turn = side_effect
            
            mock_generate.side_effect = [
                # Shared Turn 1: "Hi" (Used by V1 and V2)
                GeneratedTurn(content="Hi", should_continue=True, metadata={}),
                # Shared Turn 2: "Book Paris" (Used by V1 and V2)
                GeneratedTurn(content="Book Paris", should_continue=False, metadata={}),
            ] * 2 # Enough side effects for safety if logic changes
            
            with patch("gavel_ai.core.steps.conversational_processor.ProviderFactory") as MockFactory:
                mock_factory_instance = MagicMock()
                # Important: Replace the factory on the ALREADY INSTANTIATED step
                step.provider_factory = mock_factory_instance
                
                MockFactory.return_value = mock_factory_instance
                
                # Mock call_agent to return different responses based on history/agent
                async def mock_call_agent(agent, history):
                    # Simple mock response
                    return MagicMock(
                        output="I am an AI assistant", 
                        metadata={"latency_ms": 50, "tokens": {"prompt": 10, "completion": 5}}
                    )

                mock_factory_instance.call_agent.side_effect = mock_call_agent
                
                # Execute the step
                await step.execute(run_ctx)
        
        # --- Verification ---

        # 1. Check in-memory results
        assert run_ctx.conversation_results is not None
        assert len(run_ctx.conversation_results) == 2  # 1 scenario * 2 variants
        
        variants_processed = {r.variant_id for r in run_ctx.conversation_results}
        assert variants_processed == {"variant-1", "variant-2"}
        
        # 2. Verify Determinism Check Passed
        # (Should be empty list if no violations)
        assert run_ctx.determinism_violations == []

        # 3. Verify Filesystem Persistence
        
        # Check results_raw.jsonl
        results_raw_path = run_ctx.run_dir / "results_raw.jsonl"
        assert results_raw_path.exists()
        
        raw_lines = results_raw_path.read_text().strip().splitlines()
        # Expect: 2 variants * 1 assistant turn (since Turn 2 stops immediately) = 2 records
        # Wait, Turn 1 is "Hi", then assistant replies. Then Turn 2 "Book Paris" -> Stop.
        # So 1 assistant response per variant.
        assert len(raw_lines) == 2
        
        raw_records = [json.loads(line) for line in raw_lines]
        raw_variants = {r["variant_id"] for r in raw_records}
        assert raw_variants == {"variant-1", "variant-2"}
        
        # Check conversations.jsonl
        conversations_path = run_ctx.run_dir / "conversations.jsonl"
        assert conversations_path.exists()
        
        conv_lines = conversations_path.read_text().strip().splitlines()
        assert len(conv_lines) == 2
        
        conv_records = [json.loads(line) for line in conv_lines]
        for record in conv_records:
            assert record["scenario_id"] == "s1"
            assert record["completed"] is True
            # Check conversation structure
            turns = record["conversation_transcript"]["turns"]
            # Turn 1 (User), Turn 1 (Assist)
            # Logic: Turn 2 "Book Paris" had should_continue=False, so it was NOT added
            assert len(turns) == 2 
            assert turns[0]["role"] == "user"
            assert turns[0]["content"] == "Hi"
            assert turns[1]["role"] == "assistant"
            # assert turns[2]["role"] == "user"  <-- Removed
            # assert turns[2]["content"] == "Book Paris" <-- Removed
