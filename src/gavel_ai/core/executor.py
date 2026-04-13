"""
Executor for orchestrating processor execution with concurrency control.

Per Architecture Decision 3: Processor orchestration with error handling modes.
"""

import asyncio
from typing import Callable, List, Optional

from tqdm import tqdm

from gavel_ai.models.runtime import Input, ProcessorResult
from gavel_ai.processors.base import InputProcessor
from gavel_ai.telemetry import get_metadata_collector, get_tracer


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
        test_subject: Optional[str] = None,
        variant_id: Optional[str] = None,
    ):
        """
        Initialize executor.

        Args:
            processor: InputProcessor instance to execute
            parallelism: Number of concurrent tasks (default: 4)
            error_handling: "collect_all" or "fail_fast"
            test_subject: Optional test subject for TQDM display
            variant_id: Optional variant ID for TQDM display
        """
        self.processor = processor
        self.parallelism = parallelism
        self.error_handling = error_handling
        self.test_subject = test_subject or "unknown"
        self.variant_id = variant_id or "unknown"
        self.tracer = get_tracer(__name__)

    async def execute(
        self,
        inputs: List[Input],
        on_result: Optional[Callable[[Input, ProcessorResult], None]] = None,
    ) -> List[ProcessorResult]:
        """
        Execute processor against all inputs with concurrency control.

        Args:
            inputs: List of Input instances
            on_result: Optional callback invoked with (input, result) after each scenario
                       completes. Called synchronously before moving to the next batch.
                       Use this to stream results to disk as they arrive.

        Returns:
            List of ProcessorResult instances (one per input)

        Raises:
            Exception: If error_handling is "fail_fast" and any input fails
        """
        results: List[ProcessorResult] = []
        completed_count: int = 0
        failed_count: int = 0
        metadata_collector = get_metadata_collector()
        latest_scenario_id: str = ""

        # Process inputs in batches based on parallelism
        with tqdm(total=len(inputs), desc="Processing scenarios", unit="scenario") as pbar:
            for i in range(0, len(inputs), self.parallelism):
                batch = inputs[i : i + self.parallelism]

                # Create tasks for this batch with metadata tracking
                async def process_with_metadata(input_item: Input) -> ProcessorResult:
                    """Process input and track metadata."""
                    nonlocal latest_scenario_id
                    scenario_id = input_item.id
                    latest_scenario_id = scenario_id
                    metadata_collector.record_scenario_start(scenario_id)
                    try:
                        result = await self.processor.process([input_item])
                        # Success if no error
                        success = result.error is None
                        metadata_collector.record_scenario_complete(scenario_id, success)
                        return result
                    except Exception:
                        # Record failure
                        metadata_collector.record_scenario_complete(scenario_id, False)
                        raise

                tasks = [process_with_metadata(input_item) for input_item in batch]

                if self.error_handling == "fail_fast":
                    # Fail immediately on first error
                    batch_results = await asyncio.gather(*tasks)
                    for input_item, result in zip(batch, batch_results):
                        if on_result is not None:
                            on_result(input_item, result)
                        results.append(result)
                    completed_count += len(batch_results)
                else:
                    # Collect all results, including errors
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                    for i_idx, (input_item, result) in enumerate(zip(batch, batch_results)):
                        if isinstance(result, Exception):
                            # Store error in ProcessorResult
                            error_result = ProcessorResult(
                                output="", metadata={}, error=str(result)
                            )
                            if on_result is not None:
                                on_result(input_item, error_result)
                            results.append(error_result)
                            failed_count += 1
                        else:
                            if on_result is not None:
                                on_result(input_item, result)
                            results.append(result)
                            completed_count += 1

                # Update progress bar with latest scenario info
                pbar.update(len(batch))
                desc = f"Processing scenarios | {latest_scenario_id} | {self.test_subject} | {self.variant_id}"
                pbar.set_description(desc)

        return results
