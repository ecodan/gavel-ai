"""
Scenario processor step for OneShot workflow.

Responsibilities:
- Instantiate processor (PromptInputProcessor or ExternalHttpProcessor)
- Load prompt templates and render them with scenario variables
- Convert scenarios to PromptInput[] (local) or RemoteSystemInput[] (external+http)
- Execute via Executor with parallelism/error handling
- Store processor_results in context

Per Tech Spec 3.9: Extracted from run() lines 173-244.
Phase 2: Template rendering added to fix prompt loading bug.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError, ProcessorError, RunPolicyError
from gavel_ai.core.executor import Executor
from gavel_ai.core.issue_classifier import classify_message
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.models.config import ErrorPolicy
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.config import AsyncConfig
from gavel_ai.models.runtime import (
    Input,
    OutputRecord,
    ProcessorConfig,
    ProcessorResult,
    PromptInput,
    RemoteSystemInput,
    ScriptSystemInput,
)
from gavel_ai.processors.base import InputProcessor
from gavel_ai.processors.external_http_processor import ExternalHttpProcessor
from gavel_ai.processors.prompt_processor import PromptInputProcessor
from gavel_ai.processors.script_processor import ScriptInputProcessor


def _make_output_record(
    proc_result: ProcessorResult,
    input_item: Input,
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
        timing_ms=int(metadata.get("total_latency_ms", metadata.get("latency_ms", 0))),
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

    def _validate_prompt_placeholders(
        self, template_text: str, scenarios: List[Any], prompt_ref: str
    ) -> None:
        """Validate that every {{var}} placeholder in the template resolves from scenario fields.

        Raises:
            ConfigError: If any placeholder has no corresponding field in any scenario.
        """
        placeholders: Set[str] = set(re.findall(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}", template_text))
        if not placeholders:
            raise ConfigError(
                f"Prompt template '{prompt_ref}' contains no {{{{var}}}} placeholders. "
                "Use {{input}} (string scenarios) or {{field}} (dict scenarios) to inject scenario data."
            )

        # Build available keys from the first scenario as representative
        sample = scenarios[0] if scenarios else None
        if sample is None:
            return
        if isinstance(sample.input, dict):
            available: Set[str] = set(sample.input.keys())
        else:
            available = {"input"}
        if sample.metadata:
            available.update(sample.metadata.keys())

        missing = placeholders - available
        if missing:
            raise ConfigError(
                f"Prompt template '{prompt_ref}' references placeholder(s) {sorted(missing)} "
                f"that are not present in scenarios. Available fields: {sorted(available)}"
            )

    def _render_template(self, template_text: str, variables: Dict[str, Any]) -> str:
        """
        Render a prompt template with scenario variables using {{var}} syntax.

        Args:
            template_text: Template string using {{var}} syntax (e.g., "... {{html}}")
            variables: Dict of scenario variables (e.g., {"html": "...", "url": "..."})

        Returns:
            Rendered prompt with variables substituted

        Raises:
            ProcessorError: If a placeholder key is missing from variables
        """
        def _replace(m: re.Match) -> str:  # type: ignore[type-arg]
            key = m.group(1)
            if key not in variables:
                raise ProcessorError(
                    f"Template variable '{{{{{key}}}}}' not found in scenario. "
                    f"Available keys: {sorted(variables.keys())}"
                )
            return str(variables[key])

        return re.sub(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}", _replace, template_text)

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
        error_policy: ErrorPolicy = eval_config.error_policy

        if not eval_config.variants:
            raise ConfigError("No variants configured in eval_config")

        test_subject_config = eval_config.test_subjects[0] if eval_config.test_subjects else None
        if not test_subject_config:
            raise ConfigError("No test_subjects configured in eval_config")

        # Load and validate prompt template for local (prompt-based) evals only
        template_text: str = ""
        prompt_ref: str = ""
        inputs: List[Input] = []

        if eval_config.test_subject_type == "local":
            prompt_name = test_subject_config.prompt_name or "unknown"
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

            self._validate_prompt_placeholders(template_text, scenarios, prompt_ref)

            # Convert scenarios to PromptInput with rendered prompts (shared across all variants)
            for scenario in scenarios:
                if isinstance(scenario.input, dict):
                    variables: Dict[str, Any] = dict(scenario.input)
                else:
                    variables = {"input": str(scenario.input)}
                if scenario.metadata:
                    variables = {**variables, **scenario.metadata}

                rendered_prompt = self._render_template(template_text, variables)
                prompt_input = PromptInput(
                    id=scenario.scenario_id,
                    user=rendered_prompt,
                    system=None,
                    metadata={
                        "scenario_input": scenario.input,
                        "template": prompt_ref,
                        **(scenario.metadata or {}),
                    },
                )
                inputs.append(prompt_input)

            self.logger.info(f"Created {len(inputs)} PromptInput objects with rendered templates")

        elif (
            eval_config.test_subject_type == "external"
            and test_subject_config.protocol == "http"
        ):
            subject_config: Dict[str, Any] = test_subject_config.config or {}
            endpoint = subject_config.get("endpoint")
            if not endpoint:
                raise ConfigError(
                    "TestSubject.config.endpoint is required for protocol='http' - "
                    "Add endpoint to test_subjects[0].config in eval_config.json"
                )
            method: str = str(subject_config.get("method", "POST"))
            base_headers: Dict[str, str] = dict(subject_config.get("headers") or {})
            auth: Any = subject_config.get("auth")
            for scenario in scenarios:
                body: Dict[str, Any] = {"scenario_id": scenario.id, "input": scenario.input}
                if scenario.metadata:
                    body["metadata"] = scenario.metadata
                inputs.append(
                    RemoteSystemInput(
                        id=scenario.id,
                        endpoint=endpoint,
                        method=method,
                        headers=base_headers,
                        body=body,
                        auth=auth,
                    )
                )
            self.logger.info(
                f"Created {len(inputs)} RemoteSystemInput objects for external+http"
            )

        elif (
            eval_config.test_subject_type == "external"
            and test_subject_config.protocol == "script"
        ):
            subject_config_s: Dict[str, Any] = test_subject_config.config or {}
            command: List[Any] = subject_config_s.get("command")
            if not command or not isinstance(command, list):
                raise ConfigError(
                    "TestSubject.config.command is required and must be a list for protocol='script' - "
                    "Add command to test_subjects[0].config in eval_config.json"
                )
            request_filename: str = str(subject_config_s.get("request_filename", "request.json"))
            response_filename: str = str(subject_config_s.get("response_filename", "response.json"))
            for scenario in scenarios:
                request_payload: Dict[str, Any] = {
                    "scenario_id": scenario.id,
                    "input": scenario.input,
                }
                if scenario.metadata:
                    request_payload["metadata"] = scenario.metadata
                inputs.append(
                    ScriptSystemInput(
                        id=scenario.id,
                        command=[str(c) for c in command],
                        request_payload=request_payload,
                        request_filename=request_filename,
                        response_filename=response_filename,
                    )
                )
            self.logger.info(
                f"Created {len(inputs)} ScriptSystemInput objects for external+script"
            )

        models = agents_config.get("_models", {})
        all_records: List[OutputRecord] = []
        first_test_subject: str = ""

        # Outer loop over all variants
        for variant in eval_config.variants:
            # Resolve model definition for this variant
            if variant in models:
                model_data = models[variant]
                test_subject: str = (
                    test_subject_config.system_id
                    if eval_config.test_subject_type == "external"
                    else test_subject_config.prompt_name
                ) or "unknown"
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

            # Determine processor type based on test_subject_type and protocol
            if eval_config.test_subject_type == "local":
                processor_type: str = "prompt_input"
            elif (
                eval_config.test_subject_type == "external"
                and test_subject_config.protocol == "http"
            ):
                processor_type = "external_http"
            elif (
                eval_config.test_subject_type == "external"
                and test_subject_config.protocol == "script"
            ):
                processor_type = "external_script"
            else:
                processor_type = "external_http"

            self.logger.info(
                f"Executing variant '{variant}' ({processor_type}) "
                f"for {len(scenarios)} scenarios"
            )

            # Create processor config
            processor_config = ProcessorConfig(
                processor_type=processor_type,
                parallelism=async_config.num_workers,
                timeout_seconds=async_config.task_timeout_seconds,
                error_handling="collect_all",
            )

            # Instantiate appropriate processor
            processor: InputProcessor
            if processor_type == "prompt_input":
                processor = PromptInputProcessor(
                    config=processor_config,
                    model_def=model_def,
                )
            elif processor_type == "external_http":
                subject_cfg = test_subject_config.config or {}
                processor = ExternalHttpProcessor(
                    config=processor_config,
                    abort_on_exec_failure=test_subject_config.abort_on_exec_failure,
                    abort_on_process_error=test_subject_config.abort_on_process_error,
                    trace_header=subject_cfg.get("trace_header", "X-Gavel-Trace-Id"),
                    adapter=test_subject_config.adapter or "gavel",
                )
            elif processor_type == "external_script":
                processor = ScriptInputProcessor(
                    config=processor_config,
                    abort_on_exec_failure=test_subject_config.abort_on_exec_failure,
                    abort_on_process_error=test_subject_config.abort_on_process_error,
                    adapter=test_subject_config.adapter or "gavel",
                )
            else:
                raise ConfigError(
                    f"Unknown processor_type '{processor_type}' - "
                    f"Use 'prompt_input', 'external_http', or 'external_script'"
                )

            def _spool_result(input_item: Input, result: ProcessorResult) -> None:
                """Convert result to OutputRecord, stream to disk, accumulate in list.

                For external runner results, uses the pre-computed metadata["external_tier"]
                rather than re-deriving the tier via classify_message.

                Raises RunPolicyError immediately when the error policy requires halting.
                """
                record = _make_output_record(result, input_item, test_subject, model_variant)
                context.results_raw.append(record)
                all_records.append(record)

                if result.error is not None:
                    tier = result.metadata.get("external_tier") or classify_message(result.error)
                    log_msg = f"scenario {input_item.id} failed [{tier}]: {result.error}"
                    self.logger.error(log_msg)
                    context.run_logger.error(log_msg)
                    if error_policy.should_halt(tier):
                        raise RunPolicyError(log_msg, tier=tier, cause=Exception(result.error))

            executor = Executor(
                processor=processor,
                parallelism=async_config.num_workers,
                error_handling="collect_all",
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
