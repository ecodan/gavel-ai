"""
Conversational processing step for multi-turn dialogue evaluation.

Responsibilities:
- Orchestrate multi-turn conversation execution across scenarios × variants
- Use TurnGenerator for dynamic user turn generation
- Execute conversations with deterministic user turns across variants
- Store conversation transcripts and results in context

Per TDD Conversational Evaluation: ConversationalProcessingStep is a Step,
following the same pattern as ScenarioProcessorStep for OneShot.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime  # type: ignore[attr-defined]
from typing import Any, Dict, List, Optional

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.config import ConversationalConfig
from gavel_ai.models.conversation import (
    ConversationResult,
    ConversationScenario,
    ConversationState,
    TurnMetadata,
    TurnResult,
)
from gavel_ai.conversational.errors import classify_error
from gavel_ai.core.execution.retry_logic import call_with_retry
from gavel_ai.models.runtime import OutputRecord
from gavel_ai.processors.turn_generator import TurnGenerator
from gavel_ai.providers.factory import ProviderFactory
from gavel_ai.telemetry import get_tracer


class ConversationalProcessingStep(Step):
    """
    Multi-turn dialogue execution step.

    Orchestrates conversation execution for scenarios × variants,
    ensuring deterministic user turns across all variants of the same scenario.

    Per TDD Architecture:
    - Inherits from Step (not InputProcessor)
    - Reads config from RunContext
    - Writes results to RunContext
    - Follows same pattern as ScenarioProcessorStep
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize ConversationalProcessingStep.

        Args:
            logger: Logger for step execution (class-level logging)
        """
        super().__init__(logger)
        self.provider_factory = ProviderFactory()
        self.tracer = get_tracer(__name__)

    @property
    def phase(self) -> StepPhase:
        """Return the workflow phase for this step."""
        return StepPhase.SCENARIO_PROCESSING

    async def execute(self, context: RunContext) -> None:
        """
        Execute conversational evaluation across scenarios × variants.

        Reads configuration from context, executes conversations,
        and stores results in context for downstream steps.

        Args:
            context: RunContext for reading configs and writing results

        Raises:
            ConfigError: If configuration is invalid
            ProcessorError: If conversation execution fails
        """
        # Read configuration from context
        eval_config = context.eval_context.eval_config.read()
        agents_config = context.eval_context.agents.read()

        # Validate workflow type
        if eval_config.workflow_type != "conversational":
            raise ConfigError(
                f"ConversationalProcessingStep requires workflow_type='conversational', "
                f"got '{eval_config.workflow_type}'"
            )

        # Get conversational config
        conv_config: ConversationalConfig = eval_config.conversational
        if conv_config is None:
            raise ConfigError(
                "Conversational config not found - Add 'conversational' section to eval_config.json"
            )

        # Get variants
        variants: List[str] = eval_config.variants
        if not variants:
            raise ConfigError("No variants configured in eval_config")

        # Load scenarios (as ConversationScenario)
        scenarios = self._load_conversation_scenarios(context)
        if not scenarios:
            raise ConfigError("No scenarios found for conversational evaluation")

        # Get turn generator model definition
        turn_gen_model_def = self._get_model_definition(
            agents_config, conv_config.turn_generator.model_id
        )

        # Resolve all variants to their model definitions and prompt references
        # Per AC #1: one entry per agent with: id, model_id, model_def, prompt_ref
        resolved_variants = []
        for v_id in variants:
            try:
                m_def, p_ref = self._resolve_variant(agents_config, v_id)
                resolved_variants.append({"id": v_id, "model_def": m_def, "prompt_ref": p_ref})
            except ConfigError as e:
                self.logger.warning(f"Skipping variant '{v_id}': {e}")

        if not resolved_variants:
            raise ConfigError("No valid variants could be resolved from eval_config")

        # Get concurrency limits
        max_concurrent = eval_config.execution.max_concurrent if eval_config.execution else 5
        semaphore = asyncio.Semaphore(max_concurrent)

        # Execute conversations
        self.logger.info(
            f"Executing {len(scenarios)} scenarios × {len(variants)} variants "
            f"(concurrency={max_concurrent})"
        )

        async def _run_scenario(scenario: ConversationScenario) -> List[ConversationResult]:
            async with semaphore:
                # Create ONE TurnGenerator per scenario (shared across all variants)
                # This ensures deterministic user turns across variants (AC #2)
                turn_generator = TurnGenerator(
                    scenario=scenario,
                    model_def=turn_gen_model_def,
                    max_turns=conv_config.max_turns,
                )
                return await self._execute_scenario_variants(
                    context=context,
                    scenario=scenario,
                    variants=resolved_variants,
                    turn_generator=turn_generator,
                    conv_config=conv_config,
                )

        # Gather results for all scenarios in parallel
        scenario_tasks = [_run_scenario(s) for s in scenarios]
        scenario_results_lists = await asyncio.gather(*scenario_tasks)

        # Aggregate results
        all_results: List[ConversationResult] = []
        determinism_violations: List[Dict[str, Any]] = []

        for scenario_results in scenario_results_lists:
            all_results.extend(scenario_results)
            # Validate determinism across variants for this scenario
            if scenario_results:
                violation = self._validate_determinism(
                    scenario_results[0].scenario_id, scenario_results
                )
                if violation:
                    determinism_violations.append(violation)

        # Store results in context
        context.conversation_results = all_results
        context.determinism_violations = determinism_violations

        # Log summary
        successful = sum(1 for r in all_results if not r.error)
        failed = sum(1 for r in all_results if r.error)
        self.logger.info(
            f"Completed {len(all_results)} conversations: "
            f"{successful} successful, {failed} failed, "
            f"{len(determinism_violations)} determinism violations"
        )

        # Set test_subject and model_variant for downstream steps
        if eval_config.test_subjects:
            context.test_subject = eval_config.test_subjects[0].prompt_name or "conversational"
        else:
            context.test_subject = "conversational"
        context.model_variant = variants[0] if variants else "unknown"

    def _load_conversation_scenarios(self, context: RunContext) -> List[ConversationScenario]:
        """
        Load scenarios from context and convert to ConversationScenario.

        Args:
            context: RunContext with scenarios data source

        Returns:
            List of ConversationScenario objects
        """
        raw_scenarios = context.eval_context.scenarios.read()
        scenarios: List[ConversationScenario] = []

        for raw in raw_scenarios:
            # Handle both Scenario model and dict
            if hasattr(raw, "model_dump"):
                data = raw.model_dump()
            else:
                data = raw

            # Map fields: id/scenario_id → scenario_id, input → user_goal
            scenario_id = data.get("scenario_id") or data.get("id")
            user_goal = data.get("user_goal") or data.get("input")
            context_text = data.get("context")
            dialogue_guidance = data.get("dialogue_guidance")

            if not scenario_id or not user_goal:
                self.logger.warning("Skipping invalid scenario: missing scenario_id or user_goal")
                continue

            scenarios.append(
                ConversationScenario(
                    scenario_id=scenario_id,
                    user_goal=user_goal if isinstance(user_goal, str) else str(user_goal),
                    context=context_text,
                    dialogue_guidance=dialogue_guidance,
                )
            )

        return scenarios

    def _resolve_variant(
        self, agents_config: dict, variant_id: str
    ) -> tuple[ModelDefinition, Optional[str]]:
        """
        Resolve variant ID to ModelDefinition and prompt reference.

        Args:
            agents_config: The agents configuration dict
            variant_id: Variant ID to look up (can be model name or agent name)

        Returns:
            Tuple of (ModelDefinition, prompt_ref)

        Raises:
            ConfigError: If variant not found or invalid
        """
        models = agents_config.get("_models", {})

        # 1. Check if it's an agent name (has priority)
        if variant_id in agents_config and variant_id != "_models":
            agent = agents_config[variant_id]
            model_id = agent.get("model_id")
            if not model_id or model_id not in models:
                raise ConfigError(
                    f"Agent '{variant_id}' model_id '{model_id}' not found in _models"
                )

            prompt_ref = agent.get("prompt")
            model_def = ModelDefinition.model_validate(models[model_id])
            return model_def, prompt_ref

        # 2. Check if it's a direct model name
        if variant_id in models:
            model_def = ModelDefinition.model_validate(models[variant_id])
            return model_def, None

        raise ConfigError(
            f"Variant '{variant_id}' not found in _models or agents - "
            f"Add '{variant_id}' to agents.json"
        )

    def _get_model_definition(self, agents_config: dict, model_id: str) -> ModelDefinition:
        """
        Get model definition from agents config.

        Args:
            agents_config: The agents configuration dict
            model_id: Model ID to look up (can be model name or agent name)

        Returns:
            ModelDefinition instance

        Raises:
            ConfigError: If model not found
        """
        m_def, _ = self._resolve_variant(agents_config, model_id)
        return m_def

    async def _execute_scenario_variants(
        self,
        context: RunContext,
        scenario: ConversationScenario,
        variants: List[dict],
        turn_generator: TurnGenerator,
        conv_config: ConversationalConfig,
    ) -> List[ConversationResult]:
        """
        Execute a scenario against multiple variants in parallel turn-by-turn.

        This ensures shared user turns are generated exactly once per turn
        and used across all variants simultaneously.

        Args:
            context: RunContext for saving results
            scenario: Conversation scenario to execute
            variants: List of resolved variant dicts (id, model_def, prompt_ref)
            turn_generator: Shared TurnGenerator instance for this scenario
            max_turns: Maximum turns per conversation

        Returns:
            List of ConversationResult (one per variant)
        """
        start_time = time.time()
        v_ids = [v["id"] for v in variants]

        # Get test subject name
        eval_config = context.eval_context.eval_config.read()
        test_subject = (
            eval_config.test_subjects[0].prompt_name
            if eval_config.test_subjects
            else "conversational"
        )

        # Initialize conversation state for each variant
        variant_convs: Dict[str, ConversationState] = {
            v_id: ConversationState(
                scenario_id=scenario.scenario_id,
                variant_id=v_id,
                metadata=None,
            )
            for v_id in v_ids
        }

        # Initialize results and agents for each variant
        results_raw: Dict[str, List[TurnResult]] = {v_id: [] for v_id in v_ids}
        variant_agents: Dict[str, Any] = {}
        variant_errors: Dict[str, Optional[str]] = {v_id: None for v_id in v_ids}

        for v in variants:
            v_id = v["id"]
            try:
                # TODO: Pass system prompt from v["prompt_ref"] if supported by factory
                variant_agents[v_id] = self.provider_factory.create_agent(v["model_def"])
            except Exception as e:
                variant_errors[v_id] = f"Agent setup failed: {str(e)}"

        try:
            try:
                # Generate initial user turn (once per scenario)
                # Use the first variant's conversation state as initial context (it's empty)
                generated_turn, retry_count = await call_with_retry(
                    lambda: turn_generator.generate_turn(scenario, list(variant_convs.values())[0]),
                    conv_config.retry_config,
                )

                # Record turn generation telemetry
                with self.tracer.start_as_current_span("initial_turn_generation") as span:
                    span.set_attribute("scenario_id", scenario.scenario_id)
                    span.set_attribute("retry_count", retry_count)
            except Exception as e:
                error_type, _ = classify_error(e)
                error_msg = f"Initial turn generation failed: {str(e)}"
                self.logger.error(error_msg)
                
                # Record telemetry
                with self.tracer.start_as_current_span("initial_turn_generation_error") as span:
                    span.record_exception(e)
                    span.set_attribute("error_type", error_type)
                    span.set_attribute("scenario_id", scenario.scenario_id)
                    span.set_attribute("retry_count", conv_config.retry_config.max_retries)

                # Persist to results_raw for all variants
                for v_id in v_ids:
                    context.results_raw.append(
                        OutputRecord(
                            test_subject=test_subject,
                            variant_id=v_id,
                            scenario_id=scenario.scenario_id,
                            processor_output="",
                            timing_ms=0,
                            tokens_prompt=0,
                            tokens_completion=0,
                            error=error_msg,
                            timestamp=datetime.now(UTC).isoformat(),
                            metadata={
                                "turn_number": 0,
                                "error_type": error_type,
                            },
                        )
                    )
                raise # Re-raise to be caught by scenario-level handler which handles variant_errors and fallback results

            # Extract common turn metadata
            turn_gen_metadata = generated_turn.metadata or {}
            user_turn_metadata = TurnMetadata(
                tokens_prompt=(turn_gen_metadata.get("tokens") or {}).get("prompt"),
                tokens_completion=(turn_gen_metadata.get("tokens") or {}).get("completion"),
                latency_ms=turn_gen_metadata.get("latency_ms"),
                extra=turn_gen_metadata.get("extra"),
            )

            # Add initial user turn to all variants
            for conv in variant_convs.values():
                conv.add_turn("user", generated_turn.content, user_turn_metadata)

            turn_count = 0
            while generated_turn.should_continue and turn_count < conv_config.max_turns:
                turn_count += 1

                # Execute assistant responses in parallel for all variants
                assistant_tasks = []
                active_variants = [v_id for v_id in v_ids if not variant_errors[v_id]]

                if not active_variants:
                    break

                for v_id in active_variants:
                    agent = variant_agents[v_id]
                    conv = variant_convs[v_id]
                    task = call_with_retry(
                        lambda a=agent, c=conv: self.provider_factory.call_agent(a, c.history),
                        conv_config.retry_config,
                    )
                    assistant_tasks.append(task)

                assistant_results = await asyncio.gather(*assistant_tasks, return_exceptions=True)

                # Process results for each variant
                for v_id, response in zip(active_variants, assistant_results, strict=False):
                    conv = variant_convs[v_id]

                    if isinstance(response, BaseException):
                        error_type, _ = classify_error(response)
                        self.logger.error(f"Assistant call failed for variant {v_id}: {response}")
                        error_msg = f"Assistant call failed: {str(response)}"
                        variant_errors[v_id] = error_msg

                        # Task 6: Add Telemetry for Errors
                        with self.tracer.start_as_current_span("assistant_call_error") as span:
                            span.record_exception(response)
                            span.set_attribute("error_type", error_type)
                            span.set_attribute("scenario_id", scenario.scenario_id)
                            span.set_attribute("variant_id", v_id)
                            span.set_attribute("turn_number", len(conv.turns))
                            span.set_attribute("retry_count", conv_config.retry_config.max_retries)

                        # Task 5: Track Errors in results_raw
                        context.results_raw.append(
                            OutputRecord(
                                test_subject=test_subject,
                                variant_id=v_id,
                                scenario_id=scenario.scenario_id,
                                processor_output="",
                                timing_ms=0,
                                tokens_prompt=0,
                                tokens_completion=0,
                                error=error_msg,
                                timestamp=datetime.now(UTC).isoformat(),
                                metadata={
                                    "turn_number": len(conv.turns),
                                    "error_type": error_type,
                                },
                            )
                        )
                        continue

                    # Success: extract and add assistant response
                    actual_response, retry_count = response
                    assistant_response = actual_response.output
                    meta = actual_response.metadata

                    tokens_p = meta.get("tokens", {}).get("prompt", 0)
                    tokens_c = meta.get("tokens", {}).get("completion", 0)
                    latency = meta.get("latency_ms", 0)

                    conv.add_turn(
                        "assistant",
                        assistant_response,
                        TurnMetadata(
                            latency_ms=latency,
                            tokens_prompt=tokens_p,
                            tokens_completion=tokens_c,
                        ),
                    )

                    # Add success telemetry with retry count
                    with self.tracer.start_as_current_span("assistant_call_success") as span:
                        span.set_attribute("scenario_id", scenario.scenario_id)
                        span.set_attribute("variant_id", v_id)
                        span.set_attribute("retry_count", retry_count)

                    # Store in TurnResult (in-memory)
                    turn_result = TurnResult(
                        turn_number=len(conv.turns) - 1,
                        processor_output=assistant_response,
                        latency_ms=latency,
                        tokens_prompt=tokens_p,
                        tokens_completion=tokens_c,
                        scenario_id=scenario.scenario_id,
                        variant_id=v_id,
                    )
                    results_raw[v_id].append(turn_result)

                    # Persist to results_raw (one per turn per variant)
                    context.results_raw.append(
                        OutputRecord(
                            test_subject=test_subject,
                            variant_id=v_id,
                            scenario_id=scenario.scenario_id,
                            processor_output=assistant_response,
                            timing_ms=latency,
                            tokens_prompt=tokens_p,
                            tokens_completion=tokens_c,
                            timestamp=datetime.now(UTC).isoformat(),
                            metadata={"turn_number": len(conv.turns) - 1},
                        )
                    )

                # Generate next user turn (shared)
                # Use FIRST variant's history for coherence as authoritative history
                # We only pick a variant that hasn't failed yet
                lead_v_id = next((v_id for v_id in v_ids if not variant_errors[v_id]), None)
                if not lead_v_id:
                    break

                # Check duration timeout (AC #1)
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms >= conv_config.max_duration_ms:
                    self.logger.warning(
                        f"Scenario {scenario.scenario_id} timed out after {elapsed_ms:.0f}ms"
                    )
                    with self.tracer.start_as_current_span("conversation_timeout") as span:
                        span.set_attribute("scenario_id", scenario.scenario_id)
                        span.set_attribute("duration_ms", elapsed_ms)
                        span.set_attribute("max_duration_ms", conv_config.max_duration_ms)
                        span.set_attribute("turn_count", turn_count)
                    break

                try:
                    generated_turn, retry_count = await call_with_retry(
                        lambda: turn_generator.generate_turn(scenario, variant_convs[lead_v_id]),
                        conv_config.retry_config,
                    )

                    # Record turn generation telemetry
                    with self.tracer.start_as_current_span("turn_generation") as span:
                        span.set_attribute("scenario_id", scenario.scenario_id)
                        span.set_attribute("retry_count", retry_count)
                        span.set_attribute("turn_number", turn_count)
                except Exception as e:
                    error_type, _ = classify_error(e)
                    error_msg = f"Turn generation failed: {str(e)}"
                    self.logger.error(error_msg)

                    # Record telemetry
                    with self.tracer.start_as_current_span("turn_generation_error") as span:
                        span.record_exception(e)
                        span.set_attribute("error_type", error_type)
                        span.set_attribute("scenario_id", scenario.scenario_id)
                        span.set_attribute("turn_number", turn_count)
                        span.set_attribute("retry_count", conv_config.retry_config.max_retries)

                    # Persist to results_raw for all active variants
                    for v_id in active_variants:
                        if not variant_errors[v_id]:
                            variant_errors[v_id] = error_msg
                            context.results_raw.append(
                                OutputRecord(
                                    test_subject=test_subject,
                                    variant_id=v_id,
                                    scenario_id=scenario.scenario_id,
                                    processor_output="",
                                    timing_ms=0,
                                    tokens_prompt=0,
                                    tokens_completion=0,
                                    error=error_msg,
                                    timestamp=datetime.now(UTC).isoformat(),
                                    metadata={
                                        "turn_number": turn_count,
                                        "error_type": error_type,
                                    },
                                )
                            )
                    break

                if generated_turn.should_continue:
                    # Extract turn metadata
                    turn_gen_metadata = generated_turn.metadata or {}
                    user_turn_metadata = TurnMetadata(
                        tokens_prompt=(turn_gen_metadata.get("tokens") or {}).get("prompt"),
                        tokens_completion=(turn_gen_metadata.get("tokens") or {}).get("completion"),
                        latency_ms=turn_gen_metadata.get("latency_ms"),
                        extra=turn_gen_metadata.get("extra"),
                    )
                    # Add user turn to all active variants
                    for v_id in active_variants:
                        if not variant_errors[v_id]:
                            variant_convs[v_id].add_turn(
                                "user", generated_turn.content, user_turn_metadata
                            )

            # Finalize results for all variants
            final_results = []
            duration_ms = int((time.time() - start_time) * 1000)

            for v_id in v_ids:
                conv = variant_convs[v_id]
                error = variant_errors[v_id]

                # Compute total tokens
                tokens_total = sum(
                    (r.tokens_prompt or 0) + (r.tokens_completion or 0) for r in results_raw[v_id]
                )

                final_result = ConversationResult(
                    scenario_id=scenario.scenario_id,
                    variant_id=v_id,
                    conversation_transcript=conv,
                    results_raw=results_raw[v_id],
                    duration_ms=duration_ms,
                    completed=(
                        not generated_turn.should_continue
                        or turn_count >= conv_config.max_turns
                        if not error
                        else False
                    ),
                    tokens_total=tokens_total,
                    error=error,
                    timestamp=datetime.now(UTC),
                )
                final_results.append(final_result)

                # Persist full transcript to conversations.jsonl
                context.conversations.append(final_result)

            return final_results

        except Exception as e:
            self.logger.exception(f"Fatal error in scenario {scenario.scenario_id} execution")
            
            error_type, _ = classify_error(e)
            with self.tracer.start_as_current_span("scenario_fatal_error") as span:
                span.record_exception(e)
                span.set_attribute("scenario_id", scenario.scenario_id)
                span.set_attribute("error_type", error_type)

            # Fallback for catastrophic failure
            duration_ms = int((time.time() - start_time) * 1000)
            fallback_results = [
                ConversationResult(
                    scenario_id=scenario.scenario_id,
                    variant_id=v_id,
                    conversation_transcript=variant_convs[v_id],
                    results_raw=results_raw[v_id],
                    duration_ms=duration_ms,
                    completed=False,
                    tokens_total=0,
                    error=f"Catastrophic failure: {str(e)}",
                    timestamp=datetime.now(UTC),
                )
                for v_id in v_ids
            ]
            for r in fallback_results:
                context.conversations.append(r)
            return fallback_results

    def _validate_determinism(
        self, scenario_id: str, results: List[ConversationResult]
    ) -> Optional[Dict[str, Any]]:
        """
        Validate that user turns are identical across variants of the same scenario.

        This is a critical validation for AC #2 - identical user turns across variants.

        Args:
            scenario_id: ID of the scenario being validated
            results: List of conversation results for this scenario (one per variant)

        Returns:
            Dict describing violation if found, None otherwise
        """
        if len(results) < 2:
            return None

        # Extract user turns from first conversation as baseline
        baseline = results[0]
        baseline_user_turns = [
            turn.content for turn in baseline.conversation_transcript.turns if turn.role == "user"
        ]

        # Compare with other variants
        for result in results[1:]:
            user_turns = [
                turn.content for turn in result.conversation_transcript.turns if turn.role == "user"
            ]

            if user_turns != baseline_user_turns:
                return {
                    "scenario_id": scenario_id,
                    "baseline_variant": baseline.variant_id,
                    "variant_id": result.variant_id,
                    "baseline_user_turns": baseline_user_turns,
                    "variant_user_turns": user_turns,
                }

        return None
