"""
Scenario processor step for OneShot workflow.

Responsibilities:
- Instantiate processor (PromptInputProcessor or ClosedBoxInputProcessor)
- Load prompt templates and render them with scenario variables
- Convert scenarios to PromptInput[] with rendered prompts
- Execute via Executor with parallelism/error handling
- Store processor_results in context

Per Tech Spec 3.9: Extracted from run() lines 173-244.
Phase 2: Template rendering added to fix prompt loading bug.
"""

import logging
from datetime import datetime, timezone
from string import Template
from typing import Any, Dict, List

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError, ProcessorError
from gavel_ai.core.executor import Executor
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.config import AsyncConfig
from gavel_ai.models.runtime import (
    OutputRecord,
    ProcessorConfig,
    ProcessorResult,
    PromptInput,
)
from gavel_ai.processors.closedbox_processor import ClosedBoxInputProcessor
from gavel_ai.processors.prompt_processor import PromptInputProcessor


def _make_output_record(
    proc_result: ProcessorResult,
    input_item: PromptInput,
    test_subject: str,
    variant_id: str,
) -> OutputRecord:
    """Convert a ProcessorResult to an OutputRecord.

    Args:
        proc_result: Raw processor output
        input_item: The PromptInput that was processed (carries scenario_id)
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

    Phase 2 (Template Rendering): Loads prompt templates, renders with scenario variables,
    creates PromptInput with rendered prompts.

    Sets context.processor_results with execution results.
    Sets context.test_subject and context.model_variant for downstream steps.
    """

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)

    @property
    def phase(self) -> StepPhase:
        return StepPhase.SCENARIO_PROCESSING

    def _render_template(self, template_text: str, variables: Dict[str, Any]) -> str:
        """
        Render a prompt template with scenario variables using string.Template.

        Args:
            template_text: Template string using $var or ${var} syntax (e.g., "... $html")
            variables: Dict of scenario variables (e.g., {"html": "...", "url": "..."})

        Returns:
            Rendered prompt with variables substituted

        Raises:
            ProcessorError: If template rendering fails
        """
        try:
            return Template(template_text).substitute(variables)
        except KeyError as e:
            keys = list(variables.keys())
            raise ProcessorError(
                f"Template variable {e} not found in scenario. "
                f"Available keys: {keys}"
            ) from e
        except ValueError as e:
            raise ProcessorError(f"Malformed template placeholder: {str(e)}") from e

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
        async_config = eval_config.async_config or AsyncConfig()

        if not eval_config.variants:
            raise ConfigError("No variants configured in eval_config")

        test_subject_config = eval_config.test_subjects[0] if eval_config.test_subjects else None
        if not test_subject_config:
            raise ConfigError("No test_subjects configured in eval_config")

        # Load prompt template (once per test_subject, not per scenario)
        prompt_name = test_subject_config.prompt_name or "unknown"
        # Ensure prompt reference includes version (e.g., "default:v1" or "default:latest")
        if ":" not in prompt_name:
            prompt_ref = f"{prompt_name}:latest"
        else:
            prompt_ref = prompt_name
        self.logger.info(f"Loading prompt template: {prompt_ref}")
        try:
            template_text = context.eval_context.get_prompt(prompt_ref)
        except Exception as e:
            raise ConfigError(
                f"Failed to load prompt template '{prompt_ref}': {str(e)}. "
                f"Ensure the template exists in config/prompts/"
            ) from e

        # Convert scenarios to PromptInput with rendered prompts (shared across all variants)
        inputs: List[PromptInput] = []
        for scenario in scenarios:
            # Extract variables from scenario input
            if isinstance(scenario.input, dict):
                variables = scenario.input
            else:
                # String input: expose as $input in the template
                variables = {"input": str(scenario.input)}

            # Render template with scenario variables
            rendered_prompt = self._render_template(template_text, variables)

            # Create PromptInput with rendered prompt
            prompt_input = PromptInput(
                id=scenario.scenario_id,
                user=rendered_prompt,
                system=None,  # Can be added in future if needed
                metadata={
                    "scenario_input": scenario.input,  # Preserve original for debugging
                    "template": prompt_ref,
                    **(scenario.metadata or {}),
                },
            )
            inputs.append(prompt_input)

        self.logger.info(f"Created {len(inputs)} PromptInput objects with rendered templates")

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

            def _spool_result(input_item: PromptInput, result: ProcessorResult) -> None:
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
