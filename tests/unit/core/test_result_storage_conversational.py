import pytest

pytestmark = pytest.mark.unit
import json

import pytest

from gavel_ai.core.result_storage import ConversationStorage, RawResultStorage
from gavel_ai.models.conversation import ConversationResult, ConversationState, TurnResult


class TestConversationStorage:
    @pytest.fixture
    def storage(self, temp_eval_dir):
        return ConversationStorage(temp_eval_dir / "conversations.jsonl")

    @pytest.fixture
    def sample_conversation_result(self):
        scenario_id = "test-scenario"
        variant_id = "test-variant"
        conversation = ConversationState(
            scenario_id=scenario_id,
            variant_id=variant_id,
        )
        conversation.add_turn("user", "Hello")
        conversation.add_turn("assistant", "Hi there")

        return ConversationResult(
            scenario_id=scenario_id,
            variant_id=variant_id,
            conversation_transcript=conversation,
            duration_ms=1000,
            tokens_total=20,
            completed=True,
        )

    def test_append_creates_file(self, storage, sample_conversation_result):
        storage.append(sample_conversation_result)
        assert storage.results_file.exists()

        content = storage.results_file.read_text()
        data = json.loads(content)
        assert data["scenario_id"] == "test-scenario"
        assert len(data["conversation"]) == 2
        assert data["conversation"][0]["content"] == "Hello"

    def test_append_batch(self, storage, sample_conversation_result):
        results = [sample_conversation_result, sample_conversation_result]
        storage.append_batch(results)

        lines = storage.results_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_atomic_write_implied(self, storage, sample_conversation_result):
        # ResultStorage typically handles append, but for full export we might want rewrite
        # This test just checks basic functionality
        storage.append(sample_conversation_result)
        assert storage.results_file.exists()


class TestRawResultStorage:
    @pytest.fixture
    def storage(self, temp_eval_dir):
        return RawResultStorage(temp_eval_dir / "results_raw.jsonl")

    @pytest.fixture
    def sample_turn_result(self):
        return TurnResult(
            turn_number=1,
            scenario_id="scenario-1",
            variant_id="variant-1",
            processor_output="Response",
            latency_ms=100,
            tokens_prompt=10,
            tokens_completion=5,
            error=None,
        )

    def test_append_turn_result(self, storage, sample_turn_result):
        # We need to test if we can append TurnResult and it gets converted or stored
        # The storage might expect dictionary or specific model
        # Given AC #4: "Results Raw Entry Structure"

        storage.append(sample_turn_result)

        content = storage.results_file.read_text()
        data = json.loads(content)
        assert data["scenario_id"] == "scenario-1"
        assert data["processor_output"] == "Response"
        assert "timestamp" in data  # check timestamp is added if not present?
