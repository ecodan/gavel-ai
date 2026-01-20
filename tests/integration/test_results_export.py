import json
from unittest.mock import MagicMock, patch

import pytest

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.steps.conversational_processor import ConversationalProcessingStep
from gavel_ai.models.config import ConversationalConfig, EvalConfig
from gavel_ai.models.conversation import ConversationScenario


@pytest.mark.asyncio
async def test_conversational_export_integration(temp_eval_dir):
    """
    Integration test for verifying export of conversations and raw results.
    We mock the ProviderFactory to avoid real LLM calls but use the real ConversationalProcessingStep logic.
    """

    # Setup Contexts
    eval_ctx = LocalFileSystemEvalContext("test_eval", temp_eval_dir)

    # Patch snapshot_run_config to prevent file read during init
    with patch.object(LocalRunContext, "snapshot_run_config"):
        run_ctx = LocalRunContext(eval_ctx, base_dir=temp_eval_dir / "runs", run_id="test-run")

    # Mock Configs
    mock_eval_config = MagicMock(spec=EvalConfig)
    mock_eval_config.workflow_type = "conversational"
    mock_eval_config.variants = ["variant-1", "variant-2"]
    mock_eval_config.conversational = ConversationalConfig(
        max_turns=2, turn_generator={"model_id": "tg-model"}
    )
    mock_eval_config.execution = MagicMock()
    mock_eval_config.execution.max_concurrent = 1
    mock_eval_config.test_subjects = []

    mock_model_def = {
        "model_provider": "mock",
        "model_family": "mock",
        "model_version": "1.0",
        "model_parameters": {},
        "provider_auth": {},
    }

    mock_agents_config = {
        "_models": {"model-1": mock_model_def, "tg-model": mock_model_def},
        "variant-1": {"model_id": "model-1", "prompt": "p1"},
        "variant-2": {"model_id": "model-1", "prompt": "p2"},
    }

    scenarios = [
        ConversationScenario(id="s1", user_goal="goal1"),
        ConversationScenario(id="s2", user_goal="goal2"),
    ]

    # Mock DataSources
    run_ctx.eval_context.eval_config.read = MagicMock(return_value=mock_eval_config)
    run_ctx.eval_context.agents.read = MagicMock(return_value=mock_agents_config)
    run_ctx.eval_context.scenarios.read = MagicMock(return_value=scenarios)

    # Mock ProviderFactory
    with patch("gavel_ai.core.steps.conversational_processor.ProviderFactory") as MockFactory:
        factory_instance = MockFactory.return_value

        # Mock agent creation
        factory_instance.create_agent.return_value = MagicMock()

        # Mock agent call (Assistant response)
        async def mock_call_agent(agent, history):
            return MagicMock(
                output="Assistant processed",
                metadata={"tokens": {"prompt": 10, "completion": 5}, "latency_ms": 100},
            )

        factory_instance.call_agent.side_effect = mock_call_agent

        # Mock TurnGenerator to produce deterministic user turns
        with patch("gavel_ai.core.steps.conversational_processor.TurnGenerator") as MockTG:
            tg_instance = MockTG.return_value
            # return 1 user turn then stop

            async def mock_generate(scenario, history):
                # If history is empty, generate turn. If not, stop.
                if not history.turns:
                    mock_turn = MagicMock()
                    mock_turn.content = "User said detailed thing"
                    mock_turn.should_continue = True
                    mock_turn.metadata = {
                        "tokens": {"prompt": 5, "completion": 5},
                        "latency_ms": 50,
                    }
                    return mock_turn
                else:
                    mock_turn = MagicMock()
                    mock_turn.should_continue = False
                    return mock_turn

            tg_instance.generate_turn.side_effect = mock_generate

            # Execute Step
            step = ConversationalProcessingStep(MagicMock())
            await step.execute(run_ctx)

            # Verify Exports

            # 1. conversations.jsonl
            conv_file = run_ctx.run_dir / "conversations.jsonl"
            assert conv_file.exists()
            lines = conv_file.read_text().strip().split("\n")
            # 2 scenarios * 2 variants = 4 conversations
            assert len(lines) == 4

            # Check structure of first entry
            entry = json.loads(lines[0])
            assert "scenario_id" in entry
            assert "variant_id" in entry
            assert "conversation" in entry
            assert isinstance(entry["conversation"], list)
            assert len(entry["conversation"]) >= 2  # 1 User + 1 Assistant
            assert "metadata" in entry
            assert "total_turns" in entry["metadata"]

            # 2. results_raw.jsonl
            raw_file = run_ctx.run_dir / "results_raw.jsonl"
            assert raw_file.exists()
            raw_lines = raw_file.read_text().strip().split("\n")
            # 4 conversations * 1 assistant turn each = 4 entries
            assert len(raw_lines) == 4

            raw_entry = json.loads(raw_lines[0])
            assert "scenario_id" in raw_entry
            assert "variant_id" in raw_entry
            assert "processor_output" in raw_entry
            assert raw_entry["processor_output"] == "Assistant processed"
            assert "metadata" in raw_entry
            assert "turn_number" in raw_entry["metadata"]
            assert raw_entry["metadata"]["turn_number"] == 1  # Assistant is turn 1 (0-indexed)
