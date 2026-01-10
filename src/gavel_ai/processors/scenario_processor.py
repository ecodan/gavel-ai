"""
ScenarioProcessor for multi-turn conversational evaluation.

Wraps InputProcessor to handle multi-turn conversations with context accumulation.
"""

from typing import Any, Dict, List

from gavel_ai.core.models import Input, ProcessorConfig, ProcessorResult
from gavel_ai.processors.base import InputProcessor
from gavel_ai.telemetry import get_tracer


class ScenarioProcessor(InputProcessor):
    """
    Process multi-turn conversational scenarios.

    Wraps another InputProcessor and manages conversation context across turns.
    Per Architecture Decision 3: Extensibility for conversational workflows.
    """

    def __init__(self, config: ProcessorConfig, inner_processor: InputProcessor):
        """
        Initialize scenario processor.

        Args:
            config: ProcessorConfig instance
            inner_processor: InputProcessor to wrap for multi-turn execution
        """
        super().__init__(config)
        self.inner_processor = inner_processor
        self.tracer = get_tracer(__name__)

    async def process(self, inputs: List[Input]) -> ProcessorResult:
        """
        Execute multi-turn scenario.

        Args:
            inputs: List of Input instances representing conversation turns

        Returns:
            ProcessorResult with full conversation output
        """
        conversation_history: List[Dict[str, Any]] = []
        all_outputs: List[str] = []
        aggregated_metadata: Dict[str, Any] = {"turns": len(inputs)}

        for turn_idx, input_item in enumerate(inputs):
            # Add context from previous turns to current input
            if conversation_history:
                input_item.metadata["conversation_history"] = conversation_history

            # Process current turn
            result = await self.inner_processor.process([input_item])

            # Store turn in conversation history
            conversation_history.append(
                {"turn": turn_idx + 1, "input": input_item.text, "output": result.output}
            )

            all_outputs.append(f"Turn {turn_idx + 1}: {result.output}")

            # Merge metadata
            if result.metadata:
                for key, value in result.metadata.items():
                    if key.startswith("total_"):
                        aggregated_metadata[key] = aggregated_metadata.get(key, 0) + value
                    else:
                        aggregated_metadata[f"turn_{turn_idx + 1}_{key}"] = value

        # Combine all turn outputs
        combined_output = "\n\n".join(all_outputs)

        return ProcessorResult(
            output=combined_output,
            metadata=aggregated_metadata,
        )
