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
from typing import List

from gavel_ai.core.config.agents import ModelDefinition
from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.executor import Executor
from gavel_ai.core.models import Input, ProcessorConfig
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.processors.closedbox_processor import ClosedBoxInputProcessor
from gavel_ai.processors.prompt_processor import PromptInputProcessor


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
        Execute scenarios through processor.

        Args:
            context: RunContext for reading configs and writing results

        Raises:
            ConfigError: If processor configuration fails
        """
        eval_config = context.eval_context.eval_config
        agents_config = context.eval_context.agents_config
        scenarios = context.eval_context.scenarios
        async_config = eval_config.async_config

        # Get first variant and test subject from eval_config
        variant = eval_config.variants[0] if eval_config.variants else "unknown"
        test_subject_config = eval_config.test_subjects[0] if eval_config.test_subjects else None

        if not test_subject_config:
            raise ConfigError("No test_subjects configured in eval_config")

        # Get model definition - variant can be either a model name or agent name
        models = agents_config.get("_models", {})

        # Check if variant is a direct model name
        if variant in models:
            model_id = variant
            model_data = models[model_id]
            # For local evaluations, get prompt from test_subject
            test_subject: str = test_subject_config.prompt_name or "unknown"
        # Otherwise it should be an agent name
        elif variant in agents_config:
            agent = agents_config[variant]
            model_id = agent.get("model_id")
            if not model_id or model_id not in models:
                raise ConfigError(f"Agent '{variant}' model_id '{model_id}' not found in _models")
            model_data = models[model_id]
            # Use agent's prompt if available, otherwise from test_subject
            test_subject: str = agent.get("prompt") or test_subject_config.prompt_name or "unknown"
        else:
            raise ConfigError(f"Variant '{variant}' not found in _models or agents")

        model_def = ModelDefinition.model_validate(model_data)
        model_variant: str = model_data.get("model_version", "unknown")

        # Store in context for downstream steps
        context.test_subject = test_subject
        context.model_variant = model_variant

        # Determine processor type based on test_subject_type
        processor_type: str = (
            "prompt_input" if eval_config.test_subject_type == "local" else "closedbox_input"
        )

        self.logger.info(f"Initializing {processor_type} processor for {len(scenarios)} scenarios")

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

        self.logger.debug(f"Processor initialized: {processor_type}")

        # Convert scenarios to inputs
        inputs: List[Input] = [
            Input(
                id=scenario.scenario_id,
                text=scenario.input if isinstance(scenario.input, str) else str(scenario.input),
                metadata=scenario.metadata or {},
            )
            for scenario in scenarios
        ]

        self.logger.info(
            f"Executing {len(inputs)} scenarios: "
            f"test_subject={test_subject}, variant_id={model_variant}"
        )

        # Execute scenarios
        executor = Executor(
            processor=processor,
            parallelism=async_config.num_workers,
            error_handling="fail_fast",
            test_subject=test_subject,
            variant_id=model_variant,
        )

        processor_results = await executor.execute(inputs)

        # Store results in context
        context.processor_results = processor_results

        self.logger.info(f"Executed {len(processor_results)} scenarios successfully")
