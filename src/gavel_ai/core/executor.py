"""
Executor for orchestrating processor execution with concurrency control.

Per Architecture Decision 3: Processor orchestration with error handling modes.
"""

import asyncio
from typing import List

from gavel_ai.core.models import Input, ProcessorResult
from gavel_ai.processors.base import InputProcessor
from gavel_ai.telemetry import get_tracer


class Executor:
    """
    Orchestrate processor execution with concurrency and error handling.

    Executes scenarios concurrently with configurable parallelism and error modes.
    """

    def __init__(
        self,
        processor: InputProcessor,
        parallelism: int = 4,
        error_handling: str = "collect_all",
    ):
        """
        Initialize executor.

        Args:
            processor: InputProcessor instance to execute
            parallelism: Number of concurrent tasks (default: 4)
            error_handling: "collect_all" or "fail_fast"
        """
        self.processor = processor
        self.parallelism = parallelism
        self.error_handling = error_handling
        self.tracer = get_tracer(__name__)

    async def execute(self, inputs: List[Input]) -> List[ProcessorResult]:
        """
        Execute processor against all inputs with concurrency control.

        Args:
            inputs: List of Input instances

        Returns:
            List of ProcessorResult instances (one per input)

        Raises:
            Exception: If error_handling is "fail_fast" and any input fails
        """
        with self.tracer.start_as_current_span("executor.run") as span:
            span.set_attribute("executor.parallelism", self.parallelism)
            span.set_attribute("executor.input_count", len(inputs))
            span.set_attribute("executor.error_handling", self.error_handling)

            results: List[ProcessorResult] = []

            # Process inputs in batches based on parallelism
            for i in range(0, len(inputs), self.parallelism):
                batch = inputs[i : i + self.parallelism]

                # Create tasks for this batch
                tasks = [self.processor.process([input_item]) for input_item in batch]

                if self.error_handling == "fail_fast":
                    # Fail immediately on first error
                    batch_results = await asyncio.gather(*tasks)
                    results.extend(batch_results)
                else:
                    # Collect all results, including errors
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                    for result in batch_results:
                        if isinstance(result, Exception):
                            # Store error in ProcessorResult
                            error_result = ProcessorResult(
                                output="", metadata={}, error=str(result)
                            )
                            results.append(error_result)
                        else:
                            results.append(result)

            return results
