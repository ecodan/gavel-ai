"""
Scenario processor step for OneShot workflow.

Responsibilities:
- Instantiate processor (PromptInputProcessor or ClosedBoxInputProcessor)
- Convert scenarios to Input[]
- Execute via Executor with parallelism/error handling
- Store processor_results in context

Per Tech Spec 3.9: Extracted from run() lines 173-244.
"""

import logging
from datetime import datetime, timezone
from typing import List

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.executor import Executor
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.runtime import Input, OutputRecord, ProcessorConfig, ProcessorResult
from gavel_ai.processors.closedbox_processor import ClosedBoxInputProcessor
from gavel_ai.processors.prompt_processor import PromptInputProcessor


def _make_output_record(
    proc_result: ProcessorResult,
    input_item: Input,
    test_subject: str,
    variant_id: str,
) -> OutputRecord:
    """Convert a ProcessorResult to an OutputRecord.

    Args:
        proc_result: Raw processor output
        input_item: The input that was processed (carries scenario_id)
        test_subject: Prompt/system under test name
        variant_id: Model variant identifier

    Returns:
        OutputRecord ready for storage and downstream steps
    """
    metadata = proc_result.metadata or {}
    tokens_info = metadata.get("tokens") or {}
    return OutputRecord(
        test_subject=test_subject,
        variant_id=variant_id,
        scenario_id=input_item.id,
        processor_output=str(proc_result.output),
        timing_ms=int(metadata.get("latency_ms", 0)),
        tokens_prompt=int(tokens_info.get("prompt", 0) if isinstance(tokens_info, dict) else 0),
        tokens_completion=int(
            tokens_info.get("completion", 0) if isinstance(tokens_info, dict) else 0
        ),
        error=proc_result.error,
        metadata=metadata,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


class ScenarioProcessorStep(Step):
    """
    Executes scenarios through the appropriate processor.

    Sets context.processor_results with execution results.
    Sets context.test_subject and context.model_variant for downstream steps.
    """

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)

    @property
    def phase(self) -> StepPhase:
        return StepPhase.SCENARIO_PROCESSING

    async def execute(self, context: RunContext) -> None:
        """
        Execute scenarios through processor for all variants.

        Args:
            context: RunContext for reading configs and writing results

        Raises:
            ConfigError: If processor configuration fails
        """
        eval_config = context.eval_context.eval_config.read()
        agents_config = context.eval_context.agents.read()
        scenarios = context.eval_context.scenarios.read()
        async_config = eval_config.async_config

        if not eval_config.variants:
            raise ConfigError("No variants configured in eval_config")

        test_subject_config = eval_config.test_subjects[0] if eval_config.test_subjects else None
        if not test_subject_config:
            raise ConfigError("No test_subjects configured in eval_config")

        # Convert scenarios to inputs (shared across all variants)
        inputs: List[Input] = [
            Input(
                id=scenario.scenario_id,
                text=scenario.input if isinstance(scenario.input, str) else str(scenario.input),
                metadata=scenario.metadata or {},
            )
            for scenario in scenarios
        ]

        models = agents_config.get("_models", {})
        all_records: List[OutputRecord] = []
        first_test_subject: str = ""

        # Outer loop over all variants
        for variant in eval_config.variants:
            # Resolve model definition for this variant
            if variant in models:
                model_data = models[variant]
                test_subject: str = test_subject_config.prompt_name or "unknown"
            elif variant in agents_config:
                agent = agents_config[variant]
                model_id = agent.get("model_id")
                if not model_id or model_id not in models:
                    raise ConfigError(
                        f"Agent '{variant}' model_id '{model_id}' not found in _models"
                    )
                model_data = models[model_id]
                test_subject = agent.get("prompt") or test_subject_config.prompt_name or "unknown"
            else:
                raise ConfigError(f"Variant '{variant}' not found in _models or agents")

            model_def = ModelDefinition.model_validate(model_data)
            model_variant: str = model_data.get("model_version", "unknown")

            if not first_test_subject:
                first_test_subject = test_subject

            # Determine processor type based on test_subject_type
            processor_type: str = (
                "prompt_input" if eval_config.test_subject_type == "local" else "closedbox_input"
            )

            self.logger.info(
                f"Executing variant '{variant}' ({processor_type}) "
                f"for {len(scenarios)} scenarios"
            )

            # Create processor config
            processor_config = ProcessorConfig(
                processor_type=processor_type,
                parallelism=async_config.num_workers,
                timeout_seconds=async_config.task_timeout_seconds,
                error_handling="fail_fast",
            )

            # Instantiate appropriate processor
            if processor_type == "prompt_input":
                processor = PromptInputProcessor(
                    config=processor_config,
                    model_def=model_def,
                )
            elif processor_type == "closedbox_input":
                processor = ClosedBoxInputProcessor(
                    config=processor_config,
                    model_def=model_def,
                )
            else:
                raise ConfigError(
                    f"Unknown processor_type '{processor_type}' - "
                    f"Use 'prompt_input' or 'closedbox_input'"
                )

            def _spool_result(input_item: Input, result: ProcessorResult) -> None:
                """Convert result to OutputRecord, stream to disk, accumulate in list."""
                record = _make_output_record(result, input_item, test_subject, model_variant)
                context.results_raw.append(record)
                all_records.append(record)

            executor = Executor(
                processor=processor,
                parallelism=async_config.num_workers,
                error_handling="fail_fast",
                test_subject=test_subject,
                variant_id=model_variant,
            )

            await executor.execute(inputs, on_result=_spool_result)

        # Store results in context for downstream steps
        context.processor_results = all_records
        context.test_subject = first_test_subject
        context.model_variant = ", ".join(eval_config.variants)

        self.logger.info(
            f"Executed {len(all_records)} records across "
            f"{len(eval_config.variants)} variant(s) successfully"
        )
