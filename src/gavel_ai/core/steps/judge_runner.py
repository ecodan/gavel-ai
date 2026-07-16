"""
Judge runner step for OneShot workflow.

Responsibilities:
- Extract judges from eval_config.test_subjects[]
- Resolve judge model IDs in agents_config
- Execute JudgeExecutor.execute_batch() per variant group (LLM judges)
- Execute DeterministicMetric per record (deterministic judges)
- Route external-protocol judges through ExternalHttpProcessor/ScriptInputProcessor
- Store evaluation_results, deterministic_metrics, external_judged_records in context

Per Tech Spec 3.9: Extracted from run() lines 247-318.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError, RunPolicyError
from gavel_ai.core.issue_classifier import ExternalOutcome, classify_external_outcome
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.judges.deterministic_metric import DeterministicMetric
from gavel_ai.judges.judge_executor import JudgeExecutor
from gavel_ai.judges.judge_registry import JudgeRegistry
from gavel_ai.models.config import ScenarioFieldMapping
from gavel_ai.models.runtime import (
    DeterministicRunResult,
    ExternalJudgeRequest,
    JudgedRecord,
    OutputRecord,
    ProcessorConfig,
    ProcessorResult,
    RemoteSystemInput,
    Scenario,
    ScriptSystemInput,
)
from gavel_ai.processors.external_http_processor import ExternalHttpProcessor
from gavel_ai.processors.script_processor import ScriptInputProcessor
from gavel_ai.telemetry import get_current_run_id


def _render_judge_template(template: str, context: dict) -> str:
    """Replace {{key}} placeholders with values from context; unknown keys pass through."""
    result: str = template
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def _build_render_context(scenario: Scenario) -> dict:
    """Build template render context from scenario input and metadata."""
    context: dict = {}
    if isinstance(scenario.input, dict):
        context.update(scenario.input)
    elif isinstance(scenario.input, str):
        context["input"] = scenario.input
    if scenario.metadata:
        context.update(scenario.metadata)
    return context


def _load_markdown_judge_config(markdown_path_str: str, eval_dir: Path) -> dict:
    """
    Load judge config from a Markdown file within eval_dir.

    Parses ## Criteria, ## Evaluation Steps, ## Threshold, ## Guidelines sections.
    Missing sections are silently absent from the returned dict.

    Raises:
        ConfigError: If the resolved path is outside eval_dir (path traversal).
        ConfigError: If the file does not exist.
    """
    resolved: Path = (eval_dir / markdown_path_str).resolve()
    eval_dir_resolved: Path = eval_dir.resolve()
    if not str(resolved).startswith(str(eval_dir_resolved)):
        raise ConfigError(
            f"markdown_path '{markdown_path_str}' resolves outside eval_dir '{eval_dir}' - "
            "Path traversal not allowed"
        )
    if not resolved.exists():
        raise ConfigError(
            f"markdown_path file not found: '{resolved}' - "
            "Verify the path is relative to the eval directory"
        )

    text: str = resolved.read_text(encoding="utf-8")
    result: dict = {}

    import re
    sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
    for section in sections:
        if not section.strip():
            continue
        lines = section.splitlines()
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        if heading == "Criteria":
            result["criteria"] = body
        elif heading == "Evaluation Steps":
            steps = [line.strip().lstrip("-* ").strip() for line in body.splitlines() if line.strip()]
            result["evaluation_steps"] = steps
        elif heading == "Threshold":
            try:
                result["threshold"] = float(body.strip())
            except ValueError:
                pass
        elif heading == "Guidelines":
            result["guidelines"] = body

    return result


def _resolve_scenario_field(scenario: Scenario, path: str) -> Optional[str]:
    """Resolve a dot-notation path starting from a scenario object.

    Mirrors DeepEvalJudge._resolve_field — kept here so the runner can
    validate field_mapping against scenario data without importing the judge.
    """
    node: Any = scenario
    for key in path.split("."):
        if isinstance(node, dict):
            node = node.get(key)
        elif hasattr(node, key):
            node = getattr(node, key)
        else:
            return None
        if node is None:
            return None
    if node is None:
        return None
    if isinstance(node, (dict, list)):
        return json.dumps(node)
    return str(node)


def _validate_geval_expected_output(
    judge_name: str,
    scenarios: List[Scenario],
    field_mapping: Optional[ScenarioFieldMapping],
) -> None:
    """Raise ConfigError if any scenario cannot resolve expected_output for a GEval judge.

    Called once at judge startup — fails fast before any API calls are made.
    """
    path = field_mapping.expected_output if field_mapping else None
    missing: List[str] = []

    for scenario in scenarios:
        value = (
            _resolve_scenario_field(scenario, path)
            if path
            else (scenario.expected_behavior or "")
        )
        if not value:
            missing.append(scenario.id)

    if missing:
        hint = (
            f"field_mapping.expected_output='{path}'"
            if path
            else "scenario.expected_behavior (no field_mapping.expected_output configured)"
        )
        ids_preview = ", ".join(missing[:5]) + ("..." if len(missing) > 5 else "")
        raise ConfigError(
            f"GEval judge '{judge_name}' requires expected_output but "
            f"{len(missing)} scenario(s) have none (checked {hint}): {ids_preview}. "
            f"Add expected_behavior to each scenario or set field_mapping.expected_output "
            f"in the scenarios section of eval_config.json."
        )


def _build_judge_criteria(judge_config: Any) -> str:
    """Extract and normalise the rendered judge criteria string.

    Falls back to an empty string so callers always receive a str.
    """
    if judge_config.criteria:
        return str(judge_config.criteria)
    if judge_config.config and "criteria" in judge_config.config:
        return str(judge_config.config["criteria"])
    return ""


async def _execute_external_judge(
    judge_config: Any,
    record: OutputRecord,
    scenario: Scenario,
    logger: logging.Logger,
) -> JudgedRecord:
    """Delegate a single scoring invocation to an external judge system.

    Constructs an ExternalJudgeRequest, routes it through the appropriate
    transport (http or script), parses the response envelope, and returns a
    JudgedRecord with judge_id / score / reasoning / error / metadata["trace_id"].

    The abort_on_exec_failure / abort_on_process_error flags on judge_config
    control whether a RunPolicyError is raised for non-OK outcomes, mirroring
    the identical flags on TestSubject for task execution.
    """
    trace_id: Optional[str] = get_current_run_id()
    judge_id: str = judge_config.system_id or judge_config.name
    timestamp: str = datetime.now(timezone.utc).isoformat()
    judge_cfg: Dict[str, Any] = dict(judge_config.config or {})
    adapter: str = judge_config.adapter or "gavel"

    criteria: str = _build_judge_criteria(judge_config)

    request_payload: Dict[str, Any] = ExternalJudgeRequest(
        scenario_id=record.scenario_id,
        processor_output=record.processor_output[:32768],  # 32 KB cap
        criteria=criteria,
        expected_behavior=scenario.expected_behavior,
        custom_config=judge_cfg,
        trace_id=trace_id,
        metadata={},
    ).model_dump(exclude_none=False)

    proc_config = ProcessorConfig(
        processor_type="external",
        timeout_seconds=int(judge_cfg.get("timeout", 60)),
    )

    processor_result: ProcessorResult

    if judge_config.protocol == "http":
        endpoint: str = judge_cfg.get("endpoint", "")
        method: str = judge_cfg.get("method", "POST")
        headers: Dict[str, str] = judge_cfg.get("headers", {})
        auth: Optional[Dict[str, str]] = judge_cfg.get("auth")
        trace_header: str = judge_cfg.get("trace_header", "X-Gavel-Trace-Id")

        remote_input = RemoteSystemInput(
            id=record.scenario_id,
            endpoint=endpoint,
            method=method,
            headers=headers,
            body=request_payload,
            auth=auth,
        )
        http_processor = ExternalHttpProcessor(
            proc_config,
            abort_on_exec_failure=judge_config.abort_on_exec_failure,
            abort_on_process_error=judge_config.abort_on_process_error,
            trace_header=trace_header,
            adapter=adapter,
        )
        processor_result = await http_processor.process([remote_input])

    elif judge_config.protocol == "script":
        command: List[str] = judge_cfg.get("command", [])
        working_dir: Optional[str] = judge_cfg.get("working_dir")
        request_filename: str = judge_cfg.get("request_filename", "request.json")
        response_filename: str = judge_cfg.get("response_filename", "response.json")

        script_input = ScriptSystemInput(
            id=record.scenario_id,
            command=command,
            working_dir=working_dir,
            request_payload=request_payload,
            request_filename=request_filename,
            response_filename=response_filename,
        )
        script_processor = ScriptInputProcessor(
            proc_config,
            abort_on_exec_failure=judge_config.abort_on_exec_failure,
            abort_on_process_error=judge_config.abort_on_process_error,
            adapter=adapter,
        )
        processor_result = await script_processor.process([script_input])
    else:
        raise ConfigError(
            f"External judge '{judge_config.name}' has unsupported protocol "
            f"'{judge_config.protocol}' - expected 'http' or 'script'"
        )

    # Extract external_outcome set by the processor
    outcome: Optional[ExternalOutcome] = None
    raw_outcome = processor_result.metadata.get("external_outcome")
    if raw_outcome is not None:
        try:
            outcome = ExternalOutcome(raw_outcome)
        except ValueError:
            outcome = ExternalOutcome.PROCESS_FAILURE

    # Determine IssueTier and possibly raise RunPolicyError
    tier = classify_external_outcome(
        outcome,
        abort_on_exec_failure=judge_config.abort_on_exec_failure,
        abort_on_process_error=judge_config.abort_on_process_error,
        adapter=adapter,
    )
    if tier == "ERROR" and outcome is not None:
        error_msg: str = (
            f"External judge '{judge_config.name}' outcome classified as {tier}: "
            f"{processor_result.error or 'no detail'}"
        )
        raise RunPolicyError(
            error_msg,
            tier=tier,
            cause=RuntimeError(processor_result.error or "external judge error"),
        )

    # Parse score and reasoning from the response envelope result
    score: float = 0.0
    reasoning: Optional[str] = None
    result_metadata: Dict[str, Any] = {"trace_id": trace_id or ""}

    if processor_result.output:
        try:
            output_data = json.loads(processor_result.output)
            if isinstance(output_data, dict):
                # Support flat {"score": N, "reasoning": "..."} or nested {"result": {...}}
                result_dict: Dict[str, Any] = output_data
                nested = output_data.get("result")
                if isinstance(nested, dict):
                    result_dict = nested
                raw_score = result_dict.get("score")
                if raw_score is not None:
                    score = max(0.0, min(1.0, float(raw_score)))
                reasoning = result_dict.get("reasoning")
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    result_metadata.update({
        k: v for k, v in processor_result.metadata.items()
        if k != "trace_id"
    })
    if trace_id:
        result_metadata["trace_id"] = trace_id

    return JudgedRecord(
        test_subject=record.test_subject,
        variant_id=record.variant_id,
        scenario_id=record.scenario_id,
        judge_id=judge_id,
        score=score,
        reasoning=reasoning,
        error=processor_result.error,
        timestamp=timestamp,
        metadata=result_metadata,
    )


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
    Sets context.external_judged_records with externally-delegated judge results.
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

        # Resolve config_ref → TOML file contents (merge into judge_config.config)
        for judge_config in judges_list:
            if judge_config.config_ref:
                try:
                    toml_data = context.eval_context.get_judge_config(judge_config.config_ref)
                    if judge_config.config is None:
                        judge_config.config = {}
                    judge_config.config.update(toml_data)
                    self.logger.debug(
                        f"Resolved config_ref '{judge_config.config_ref}' for judge '{judge_config.name}'"
                    )
                except ConfigError:
                    raise ConfigError(
                        f"Judge config file not found: config/judges/{judge_config.config_ref}.toml - "
                        "Create the file or remove the config_ref field"
                    )

        # Resolve markdown_path → parsed Markdown sections (merge into judge_config.config)
        eval_dir: Path = context.eval_context.eval_dir
        for judge_config in judges_list:
            if judge_config.markdown_path:
                md_data = _load_markdown_judge_config(judge_config.markdown_path, eval_dir)
                if judge_config.config is None:
                    judge_config.config = {}
                for key, value in md_data.items():
                    if key not in judge_config.config:
                        judge_config.config[key] = value
                if "criteria" in md_data and judge_config.criteria is None:
                    judge_config.criteria = md_data["criteria"]
                if "evaluation_steps" in md_data and judge_config.evaluation_steps is None:
                    judge_config.evaluation_steps = md_data["evaluation_steps"]
                if "threshold" in md_data and judge_config.threshold is None:
                    judge_config.threshold = md_data["threshold"]
                self.logger.debug(
                    f"Loaded markdown_path '{judge_config.markdown_path}' for judge '{judge_config.name}'"
                )

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

        # Inject scenarios field_mapping into each GEval judge's config dict, then
        # validate that every scenario can resolve expected_output.  Both steps happen
        # before any API call so failures are caught immediately with a clear message.
        field_mapping: Optional[ScenarioFieldMapping] = eval_config.scenarios.field_mapping
        for judge_config in judges_list:
            if judge_config.type == "deepeval.geval":
                if judge_config.config is None:
                    judge_config.config = {}
                if field_mapping:
                    judge_config.config["field_mapping"] = field_mapping.model_dump(
                        exclude_none=True
                    )
                _validate_geval_expected_output(judge_config.name, scenarios, field_mapping)

        # Apply criteria templating per record (deferred — applied in execution loop below).
        # Store a per-scenario render context builder so each record gets its scenario vars.
        # For now, apply top-level template rendering once using empty context
        # (scenario-level rendering happens per-record in the deterministic path;
        #  LLM judge criteria templating is applied here using the first scenario as preview
        #  since LLM judges receive criteria once at construction, not per-sample).
        # Per ADR-1: render criteria/evaluation_steps here before judge construction.
        for judge_config in judges_list:
            if scenarios:
                render_ctx = _build_render_context(scenarios[0])
                if judge_config.criteria:
                    judge_config.criteria = _render_judge_template(judge_config.criteria, render_ctx)
                    if judge_config.config is None:
                        judge_config.config = {}
                    judge_config.config["criteria"] = judge_config.criteria
                if judge_config.evaluation_steps:
                    judge_config.evaluation_steps = [
                        _render_judge_template(step, render_ctx)
                        for step in judge_config.evaluation_steps
                    ]
                    if judge_config.config is None:
                        judge_config.config = {}
                    judge_config.config["evaluation_steps"] = judge_config.evaluation_steps

        # Partition judges into external, LLM, and deterministic
        external_configs: List[Any] = []
        llm_configs: List[Any] = []
        det_configs: List[Any] = []
        for cfg in judges_list:
            if getattr(cfg, "protocol", None) in ("http", "script"):
                external_configs.append(cfg)
            else:
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

        # --- External judges ---
        external_judged_records: List[JudgedRecord] = []
        if external_configs:
            self.logger.info(
                f"Running {len(external_configs)} external judge(s) on "
                f"{len(processor_results)} records"
            )
            for ext_cfg in external_configs:
                for record in processor_results:
                    scenario = scenario_map.get(record.scenario_id)
                    if scenario is None:
                        self.logger.warning(
                            f"Scenario '{record.scenario_id}' not found for external judge "
                            f"'{ext_cfg.name}' - skipping record"
                        )
                        continue
                    judged = await _execute_external_judge(
                        ext_cfg, record, cast(Scenario, scenario), self.logger
                    )
                    external_judged_records.append(judged)
                    self.logger.debug(
                        f"External judge '{ext_cfg.name}' scored scenario "
                        f"'{record.scenario_id}': score={judged.score}"
                    )

        context.external_judged_records = external_judged_records
        if external_judged_records:
            self.logger.info(
                f"External judging complete: {len(external_judged_records)} JudgedRecord(s)"
            )

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
