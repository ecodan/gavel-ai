"""
DeepEval judge integration for gavel-ai.

Wraps DeepEval judges (similarity, faithfulness, hallucination, answer_relevancy, GEval)
and provides unified interface via the Judge base class.

Per Architecture Decision 5: DeepEval-native judges with sequential execution.
"""

import asyncio
import logging
import os
import tenacity
from typing import Any, Callable, Dict, Optional

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
)

from gavel_ai.core.retry import RetryConfig, retry_with_backoff
from deepeval.errors import MissingTestCaseParamsError
from deepeval.models import AnthropicModel, GeminiModel, GPTModel, OllamaModel
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from jinja2 import Template

from gavel_ai.core.exceptions import JudgeError
from gavel_ai.judges.base import Judge
from gavel_ai.models.runtime import JudgeConfig, JudgeResult, Scenario
from gavel_ai.telemetry import get_current_run_id


def _is_rate_limit_retry_error(e: Exception) -> bool:
    """
    Check if a tenacity.RetryError was caused by a rate limit error.

    DeepEval uses Tenacity to retry on transient errors. When rate-limit retries
    are exhausted, Tenacity raises RetryError. This predicate distinguishes
    rate-limit errors (which should be retried at gavel-ai level) from auth errors
    (which should fail immediately).

    Args:
        e: Exception to check (should be tenacity.RetryError)

    Returns:
        True if the underlying cause is a rate-limit error, False otherwise
    """
    if not isinstance(e, tenacity.RetryError):
        return False
    cause = e.last_attempt.exception() if e.last_attempt else None
    s = str(cause or e).lower()
    return any(k in s for k in ("rate limit", "ratelimit", "429", "too many requests"))


class DeepEvalJudge(Judge):
    """
    Judge implementation using DeepEval metrics.

    Per Epic 4 Story 4.2: Supports DeepEval built-in judges (similarity, faithfulness,
    hallucination, answer_relevancy) and custom GEval judges.

    All DeepEval scores are normalized to 1-10 scale for consistency.
    """

    # Map judge types to DeepEval metric classes
    JUDGE_TYPE_MAP = {
        "deepeval.answer_relevancy": AnswerRelevancyMetric,
        "deepeval.contextual_relevancy": ContextualRelevancyMetric,
        "deepeval.faithfulness": FaithfulnessMetric,
        "deepeval.hallucination": HallucinationMetric,
        "deepeval.geval": GEval,
    }

    def _create_model_instance(self, model_name: str, model_family: Optional[str] = None) -> Any:
        """
        Create appropriate DeepEval model instance with cost tracking disabled.

        Uses model_family from agents.json to select the correct model class:
        - "claude" → AnthropicModel (uses api_key if provided, else ANTHROPIC_API_KEY)
        - "gemini" → GeminiModel (uses api_key if provided, else GOOGLE_API_KEY)
        - "qwen" (or other Ollama) → OllamaModel (uses base_url)
        - "gpt" or None → GPTModel (uses api_key if provided, else OPENAI_API_KEY)

        Args:
            model_name: Model identifier string (e.g., "claude-sonnet-4-5-20250929")
            model_family: Model family from agents.json (e.g., "claude", "gpt", "gemini")
                         Falls back to pattern matching if None

        Returns:
            Configured DeepEvalBaseLLM subclass with cost tracking disabled (cost=0)
        """
        # Extract auth from config
        metric_config = self.config.config or {}
        api_key = metric_config.get("api_key")
        base_url = metric_config.get("base_url")

        # Resolve environment variables in API key (supports {{VAR}} and ${VAR} formats)
        if api_key:
            env_var_name = None
            if api_key.startswith("{{") and api_key.endswith("}}"):
                env_var_name = api_key[2:-2]
            elif api_key.startswith("${") and api_key.endswith("}"):
                env_var_name = api_key[2:-1]

            if env_var_name:
                resolved_key = os.getenv(env_var_name)
                # If not found in env, we'll let it be as is (maybe it's a literal for some reason, 
                # though unlikely. But deepeval will fail anyway if invalid).
                if resolved_key:
                    api_key = resolved_key
        # Model family detection - use explicit family if available
        if model_family:
            family = model_family.lower()
        else:
            # Fallback: pattern matching on model name
            model_lower = model_name.lower()
            if "claude" in model_lower:
                family = "claude"
            elif "gemini" in model_lower:
                family = "gemini"
            elif "qwen" in model_lower or "ollama" in model_lower:
                family = "qwen"  # or "ollama"
            else:
                family = "gpt"  # Default

        # Create model-family-specific instance with cost=0
        if family == "claude":
            kwargs = {
                "model": model_name,
                "cost_per_input_token": 0,
                "cost_per_output_token": 0,
            }
            if api_key:
                kwargs["api_key"] = api_key
            return AnthropicModel(**kwargs)
        elif family == "gemini":
            kwargs = {
                "model": model_name,
                "cost_per_input_token": 0,
                "cost_per_output_token": 0,
            }
            if api_key:
                kwargs["api_key"] = api_key
            return GeminiModel(**kwargs)
        elif family in ("qwen", "ollama"):
            kwargs = {
                "model": model_name,
                "cost_per_input_token": 0,
                "cost_per_output_token": 0,
            }
            if base_url:
                kwargs["base_url"] = base_url
            return OllamaModel(**kwargs)
        else:
            # Default to GPTModel for GPT and unknown families
            kwargs = {
                "model": model_name,
                "cost_per_input_token": 0,
                "cost_per_output_token": 0,
            }
            if api_key:
                kwargs["api_key"] = api_key
            return GPTModel(**kwargs)

    def __init__(self, config: JudgeConfig):
        """
        Initialize DeepEval judge with configuration.

        Args:
            config: JudgeConfig with judge type matching a DeepEval metric

        Raises:
            JudgeError: If judge type is not supported
        """
        super().__init__(config)

        judge_type = config.type
        if not judge_type or judge_type not in self.JUDGE_TYPE_MAP:
            raise JudgeError(
                f"Unsupported DeepEval judge type '{judge_type}' - "
                f"Use one of: {', '.join(self.JUDGE_TYPE_MAP.keys())}"
            )

        # Create the DeepEval metric instance
        self.metric = self._create_metric()

    def _create_metric(self) -> Any:
        """
        Create DeepEval metric instance from config.

        Returns:
            Configured DeepEval metric instance

        Raises:
            JudgeError: On metric creation failures
        """
        try:
            judge_type = self.config.type
            judge_id = self.config.name

            metric_class = self.JUDGE_TYPE_MAP[judge_type]

            # Extract metric-specific config from nested config dict
            metric_config = self.config.config.copy() if self.config.config else {}

            # Handle GEval separately (different constructor)
            if judge_type == "deepeval.geval":
                # GEval requires name, criteria, evaluation_steps, evaluation_params, model
                # Get from nested config dict
                criteria = metric_config.get("criteria", "Evaluate the quality of the response")
                evaluation_steps = metric_config.get(
                    "evaluation_steps",
                    [
                        "Check if the response answers the question",
                        "Evaluate the clarity and accuracy",
                    ],
                )
                # evaluation_params is always all three — the scenarios section
                # field_mapping (injected into config by JudgeRunnerStep) controls
                # where each value comes from.  JudgeRunnerStep validates upfront that
                # every scenario can resolve expected_output before any judge runs.
                evaluation_params = [
                    LLMTestCaseParams.INPUT,
                    LLMTestCaseParams.ACTUAL_OUTPUT,
                    LLMTestCaseParams.EXPECTED_OUTPUT,
                ]
                # Use threshold from config dict, then fall back to top-level threshold
                threshold = metric_config.get("threshold") or self.config.threshold or 0.5

                # Get model name and family from config
                model_name = metric_config.get("model") or self.config.model
                if not model_name:
                    raise JudgeError(
                        f"GEval judge '{judge_id}' requires 'model' in config - "
                        f"Specify model in judge configuration (e.g., 'claude-sonnet-4-5-20250929')"
                    )

                # Get family if available (from agents.json resolution)
                model_family = metric_config.get("model_family")

                # Create family-specific model with cost tracking disabled
                model = self._create_model_instance(model_name, model_family)

                geval_kwargs: Dict[str, Any] = dict(
                    name=metric_config.get("name", judge_id),
                    criteria=criteria,
                    evaluation_steps=evaluation_steps,
                    evaluation_params=evaluation_params,
                    model=model,
                    threshold=threshold,
                )
                # strict_mode makes GEval return binary 0/1 (normalizes to score 1 or 10)
                strict_mode = metric_config.get("strict_mode")
                if strict_mode is not None:
                    geval_kwargs["strict_mode"] = strict_mode

                return metric_class(**geval_kwargs)

            # For other judges, pass threshold and model if provided
            kwargs = {}
            # Check both metric_config and top-level config for threshold/model
            if metric_config.get("threshold") is not None:
                kwargs["threshold"] = metric_config["threshold"]
            elif self.config.threshold is not None:
                kwargs["threshold"] = self.config.threshold

            # Handle model parameter with cost=0
            if metric_config.get("model") or self.config.model:
                model_name = metric_config.get("model") or self.config.model
                model_family = metric_config.get("model_family")
                kwargs["model"] = self._create_model_instance(model_name, model_family)

            return metric_class(**kwargs)

        except Exception as e:
            judge_type = self.config.type
            raise JudgeError(
                f"Failed to create DeepEval metric '{judge_type}': {e} - "
                f"Check judge configuration and API credentials"
            ) from e

    async def evaluate(self, scenario: Scenario, subject_output: str) -> JudgeResult:
        """
        Evaluate subject output using DeepEval metric.

        Args:
            scenario: The test scenario with input and expected behavior
            subject_output: The output to evaluate

        Returns:
            JudgeResult with score (1-10), reasoning, and evidence

        Raises:
            JudgeError: On evaluation failures
        """
        with self.tracer.start_as_current_span("judge.evaluate") as span:
            judge_id = self.config.name
            judge_type = self.config.type
            run_id = get_current_run_id()
            if run_id:
                span.set_attribute("run_id", run_id)
            span.set_attribute("judge.id", judge_id)
            span.set_attribute("judge.name", judge_type)  # DeepEval metric name
            span.set_attribute("scenario.id", scenario.id)

            try:
                # Create DeepEval test case (fails fast — not retried)
                test_case = self._create_test_case(scenario, subject_output)
            except MissingTestCaseParamsError as e:
                raise JudgeError(
                    f"Judge '{judge_type}' requires fields not present in scenario '{scenario.id}': {e}. "
                    f"Add the required field to your scenario data or use a different judge."
                ) from e

            # Run metric evaluation with rate-limit retry
            # DeepEval's internal Tenacity retries up to 2x on rate limits, then raises
            # tenacity.RetryError. We retry at the gavel-ai level for rate-limit errors.
            async def _run_metric() -> None:
                await asyncio.to_thread(self.metric.measure, test_case)

            try:
                await retry_with_backoff(
                    func=_run_metric,
                    retry_config=RetryConfig(
                        max_retries=3,
                        initial_delay=5.0,    # rate limits need longer initial wait
                        max_delay=60.0,
                        backoff_factor=2.0,
                        jitter=True,          # important for future parallel eval runs
                    ),
                    transient_exceptions=(tenacity.RetryError,),
                    transient_predicate=_is_rate_limit_retry_error,
                    error_class=JudgeError,
                    error_message_template=(
                        f"DeepEval '{judge_type}' for scenario '{scenario.id}' "
                        f"exhausted rate-limit retries ({{max_retries}}): {{error}}"
                    ),
                )
            except JudgeError:
                raise
            except Exception as e:
                raise JudgeError(
                    f"DeepEval evaluation failed for scenario '{scenario.id}' "
                    f"(judge: '{judge_type}', error: {type(e).__name__}): {e}"
                ) from e

            # Extract score and normalize to 1-10
            raw_score = self.metric.score
            normalized_score = self._normalize_score(raw_score)

            # Extract reasoning from metric
            reasoning = self._extract_reasoning()

            span.set_attribute("judge.score", normalized_score)

            return JudgeResult(
                score=normalized_score,
                reasoning=reasoning,
                evidence=f"DeepEval {judge_type} score: {raw_score:.3f}",
            )

    def _create_test_case(self, scenario: Scenario, subject_output: str) -> LLMTestCase:
        """
        Create DeepEval test case from scenario and output.

        Supports:
        - Standard expected output from scenario
        - expected_output_template with Jinja2 rendering for custom scenarios
        - field_mapping (injected by JudgeRunnerStep) for dot-notation field resolution

        Args:
            scenario: The test scenario
            subject_output: The subject's output

        Returns:
            LLMTestCase instance
        """
        field_mapping: Dict[str, str] = (self.config.config or {}).get("field_mapping") or {}

        # --- input ---
        if field_mapping.get("input"):
            input_text = self._resolve_field(scenario, field_mapping["input"]) or ""
        elif isinstance(scenario.input, dict):
            input_text = (
                scenario.input.get("text") or scenario.input.get("query") or str(scenario.input)
            )
        else:
            input_text = str(scenario.input)

        # --- actual_output ---
        if field_mapping.get("actual_output"):
            actual_output = self._resolve_field(scenario, field_mapping["actual_output"]) or subject_output
        else:
            actual_output = subject_output

        # --- expected_output ---
        # field_mapping.expected_output takes precedence; _get_expected_output handles
        # expected_output_template and scenario.expected_behavior as fallbacks.
        if field_mapping.get("expected_output"):
            expected_output = self._resolve_field(scenario, field_mapping["expected_output"]) or ""
        else:
            expected_output = self._get_expected_output(scenario)

        # Build test case
        test_case_kwargs: Dict[str, Any] = {
            "input": input_text,
            "actual_output": actual_output,
            "expected_output": expected_output or None,
        }

        # Add context if available in scenario input (for dict format)
        if isinstance(scenario.input, dict) and "context" in scenario.input:
            test_case_kwargs["context"] = [scenario.input["context"]]

        # Add retrieval context if available (for dict format)
        if isinstance(scenario.input, dict) and "retrieval_context" in scenario.input:
            test_case_kwargs["retrieval_context"] = scenario.input["retrieval_context"]

        return LLMTestCase(**test_case_kwargs)

    @staticmethod
    def _resolve_field(scenario: Scenario, path: str) -> Optional[str]:
        """Resolve a dot-notation path starting from a scenario object.

        Traverses object attributes then dict keys along each segment.
        Returns the resolved value coerced to str, or None if any segment
        is missing or the resolved value is falsy.

        Examples:
            "input.query"          → scenario.input["query"]
            "metadata.expected"    → scenario.metadata["expected"]
            "expected_behavior"    → scenario.expected_behavior
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
        return str(node) if node is not None else None

    def _get_expected_output(self, scenario: Scenario) -> str:
        """
        Get expected output for the scenario.

        Priority:
        1. Render expected_output_template if available in judge config AND has required variables
        2. Use scenario.expected or scenario.expected_behavior if available

        Args:
            scenario: The test scenario

        Returns:
            Expected output string or empty string if none available
        """
        # Check for GEval expected_output_template in config
        metric_config = self.config.config.copy() if self.config.config else {}
        template_str = metric_config.get("expected_output_template")

        if template_str:
            try:
                # Render template with scenario and metadata context
                template = Template(template_str)
                context = {}

                # Add scenario input as context
                if isinstance(scenario.input, dict):
                    context.update(scenario.input)
                else:
                    context["input"] = scenario.input

                # Add metadata if available
                if scenario.metadata:
                    context.update(scenario.metadata)

                rendered = template.render(**context)

                # Check if template was fully rendered with actual values
                # Skip if rendered text has multiple consecutive spaces (indicates empty variables)
                # or if it's mostly whitespace
                if (
                    rendered.strip()
                    and "  " not in rendered
                    and len(rendered.strip()) > len(template_str) * 0.2
                ):
                    return rendered
            except Exception as e:
                # Fall through to scenario.expected on template error
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Failed to render expected_output_template: {e} - "
                    f"falling back to scenario.expected"
                )

        # Fall back to scenario expected output fields (in priority order)
        return scenario.expected or scenario.expected_behavior or scenario.expected_output or ""

    def _normalize_score(self, raw_score: float) -> int:
        """
        Normalize DeepEval score (0.0-1.0) to 1-10 scale.

        Args:
            raw_score: DeepEval score (0.0-1.0)

        Returns:
            Normalized score (1-10)
        """
        # DeepEval scores are typically 0.0-1.0
        # Map to 1-10 scale: 0.0 -> 1, 1.0 -> 10
        # Formula: 1 + (raw_score * 9)
        normalized = int(round(1 + raw_score * 9))
        return max(1, min(10, normalized))  # Clamp to 1-10

    def _extract_reasoning(self) -> str:
        """
        Extract reasoning from DeepEval metric.

        Returns:
            Reasoning string explaining the score
        """
        # Try to get reason from metric
        if hasattr(self.metric, "reason"):
            return self.metric.reason or "No reasoning provided"

        # Fallback to score explanation
        if hasattr(self.metric, "score_breakdown"):
            return str(self.metric.score_breakdown)

        judge_type = self.config.type
        return f"{judge_type} evaluation completed"
