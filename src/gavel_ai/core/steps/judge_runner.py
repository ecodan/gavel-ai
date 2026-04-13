"""
Judge runner step for OneShot workflow.

Responsibilities:
- Extract judges from eval_config.test_subjects[]
- Resolve judge model IDs in agents_config
- Execute JudgeExecutor.execute_batch() per variant group (LLM judges)
- Execute DeterministicMetric per record (deterministic judges)
- Store evaluation_results and deterministic_metrics in context

Per Tech Spec 3.9: Extracted from run() lines 247-318.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.judges.deterministic_metric import DeterministicMetric
from gavel_ai.judges.judge_executor import JudgeExecutor
from gavel_ai.judges.judge_registry import JudgeRegistry
from gavel_ai.models.runtime import DeterministicRunResult, OutputRecord


def get_model_definition(agents_config: dict, model_id: str) -> dict:
    """
    Get model definition from agents config.

    Args:
        agents_config: The agents configuration dict
        model_id: Model ID to look up (can be model name or agent name)

    Returns:
        Model definition dict with model_version, model_family, etc.

    Raises:
        ConfigError: If model not found
    """
    models = agents_config.get("_models", {})

    # Check if it's a direct model name
    if model_id in models:
        return models[model_id]

    # Check if it's an agent name that references a model
    if model_id in agents_config:
        agent = agents_config[model_id]
        referenced_model_id = agent.get("model_id")
        if referenced_model_id and referenced_model_id in models:
            return models[referenced_model_id]

    raise ConfigError(
        f"Model '{model_id}' not found in _models or agents - "
        f"Add '{model_id}' to _models section of agents.json"
    )


class JudgeRunnerStep(Step):
    """
    Executes judges on processor results.

    Sets context.evaluation_results with LLM judge evaluations.
    Sets context.deterministic_metrics with deterministic metric results.
    """

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)

    @property
    def phase(self) -> StepPhase:
        return StepPhase.JUDGING

    async def execute(self, context: RunContext) -> None:  # noqa: C901
        """
        Execute judges on processor results, grouped by variant_id.

        Args:
            context: RunContext with processor_results to evaluate

        Raises:
            ConfigError: If judge configuration fails
        """
        eval_config = context.eval_context.eval_config.read()
        agents_config = context.eval_context.agents.read()
        scenarios = context.eval_context.scenarios.read()
        processor_results: List[OutputRecord] = context.processor_results

        if processor_results is None:
            raise ConfigError(
                "JudgeRunnerStep requires processor_results - Run ScenarioProcessorStep first"
            )

        test_subject = context.test_subject or "unknown"

        # Extract judges from test_subjects
        judges_list: List[Any] = []
        if eval_config.test_subjects:
            for subject in eval_config.test_subjects:
                if subject.judges:
                    judges_list.extend(subject.judges)

        if not judges_list:
            self.logger.info("No judges configured - skipping judging")
            context.evaluation_results = []
            context.deterministic_metrics = {}
            return

        # Resolve custom model IDs in judge configurations
        for judge_config in judges_list:
            model_to_resolve = None
            if judge_config.config and "model" in judge_config.config:
                model_to_resolve = judge_config.config["model"]
            elif judge_config.model:
                model_to_resolve = judge_config.model

            if model_to_resolve:
                try:
                    model_def = get_model_definition(agents_config, model_to_resolve)
                    resolved_model: str = model_def["model_version"]
                    model_family = model_def["model_family"]

                    judge_config.model = resolved_model
                    if judge_config.config:
                        judge_config.config["model"] = resolved_model
                        judge_config.config["model_family"] = model_family

                        # Pass auth details if available
                        provider_auth = model_def.get("provider_auth", {})
                        if "api_key" in provider_auth:
                            judge_config.config["api_key"] = provider_auth["api_key"]
                        if "base_url" in provider_auth:
                            judge_config.config["base_url"] = provider_auth["base_url"]

                    self.logger.debug(
                        f"Resolved judge '{judge_config.name}' model "
                        f"'{model_to_resolve}' to '{resolved_model}'"
                    )
                except ConfigError as e:
                    self.logger.error(
                        f"Failed to resolve model for judge '{judge_config.name}': {e}"
                    )
                    raise

        # Partition judges into LLM and deterministic
        llm_configs: List[Any] = []
        det_configs: List[Any] = []
        for cfg in judges_list:
            judge_class = JudgeRegistry._registry.get(cfg.type)
            if judge_class is not None and issubclass(judge_class, DeterministicMetric):
                det_configs.append(cfg)
            else:
                llm_configs.append(cfg)

        # Build scenario lookup map
        scenario_map = {s.id: s for s in scenarios}

        # --- Deterministic metrics ---
        deterministic_metrics: Dict[str, DeterministicRunResult] = {}
        if det_configs:
            self.logger.info(f"Running {len(det_configs)} deterministic metric(s) on {len(processor_results)} records")
            for det_cfg in det_configs:
                metric: DeterministicMetric = JudgeRegistry.create(det_cfg)
                for record in processor_results:
                    scenario = scenario_map.get(record.scenario_id)
                    if scenario is None:
                        self.logger.warning(f"Scenario '{record.scenario_id}' not found for deterministic metric '{det_cfg.name}'")
                        continue
                    metric.evaluate_sample(record.scenario_id, record.processor_output, scenario)
                run_result: DeterministicRunResult = metric.compute()
                deterministic_metrics[det_cfg.name] = run_result
                self.logger.info(
                    f"Deterministic metric '{det_cfg.name}': "
                    f"population_score={run_result.population_score}, "
                    f"samples={len(run_result.samples)}"
                )

        context.deterministic_metrics = deterministic_metrics

        # --- LLM judges ---
        if not llm_configs:
            self.logger.info("No LLM judges configured")
            context.evaluation_results = []
            return

        # Group processor results by variant_id
        groups: Dict[str, List[OutputRecord]] = defaultdict(list)
        for record in processor_results:
            groups[record.variant_id].append(record)

        self.logger.info(
            f"Running {len(llm_configs)} LLM judges on {len(processor_results)} records "
            f"across {len(groups)} variant(s)"
        )

        judge_executor = JudgeExecutor(
            judge_configs=llm_configs,
            error_handling="fail_fast",
        )

        all_results = []
        for variant_id, group in groups.items():
            batch = [
                (scenario_map[r.scenario_id], r.processor_output, r.variant_id) for r in group
            ]
            results = await judge_executor.execute_batch(
                evaluations=batch,
                subject_id=test_subject,
                test_subject=test_subject,
            )
            all_results.extend(results)

        # Convert to dict format for storage
        evaluation_results_dicts: List[Dict[str, Any]] = [
            r.model_dump() if hasattr(r, "model_dump") else r for r in all_results
        ]

        context.evaluation_results = evaluation_results_dicts

        self.logger.info(f"Judging complete: {len(evaluation_results_dicts)} evaluations")
