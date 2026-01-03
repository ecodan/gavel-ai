"""
DeepEval judge integration for gavel-ai.

Wraps DeepEval judges (similarity, faithfulness, hallucination, answer_relevancy, GEval)
and provides unified interface via the Judge base class.

Per Architecture Decision 5: DeepEval-native judges with sequential execution.
"""

import asyncio
from typing import Any, Dict

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from jinja2 import Template

from gavel_ai.core.config.models import JudgeConfig
from gavel_ai.core.exceptions import JudgeError
from gavel_ai.core.models import JudgeResult, Scenario
from gavel_ai.judges.base import Judge
from gavel_ai.telemetry import get_current_run_id


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

    def __init__(self, config: JudgeConfig):
        """
        Initialize DeepEval judge with configuration.

        Args:
            config: JudgeConfig with deepeval_name matching a DeepEval metric

        Raises:
            JudgeError: If deepeval_name is not supported
        """
        super().__init__(config)

        judge_type = config.deepeval_name
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
            judge_type = self.config.deepeval_name
            judge_id = self.config.id

            metric_class = self.JUDGE_TYPE_MAP[judge_type]

            # Extract metric-specific config from nested config dict
            metric_config = self.config.config.copy() if self.config.config else {}

            # Handle GEval separately (different constructor)
            if judge_type == "deepeval.geval":
                # GEval requires name, criteria, evaluation_steps, evaluation_params
                # Get from nested config dict
                criteria = metric_config.get(
                    "criteria", "Evaluate the quality of the response"
                )
                evaluation_steps = metric_config.get(
                    "evaluation_steps",
                    [
                        "Check if the response answers the question",
                        "Evaluate the clarity and accuracy",
                    ],
                )
                # evaluation_params must be LLMTestCaseParams enum values (not strings)
                evaluation_params = [
                    LLMTestCaseParams.INPUT,
                    LLMTestCaseParams.ACTUAL_OUTPUT,
                    LLMTestCaseParams.EXPECTED_OUTPUT,
                ]
                # Use threshold from config dict, then fall back to top-level threshold
                threshold = (
                    metric_config.get("threshold")
                    or self.config.threshold
                    or 0.5
                )

                return metric_class(
                    name=metric_config.get("name", judge_id),
                    criteria=criteria,
                    evaluation_steps=evaluation_steps,
                    evaluation_params=evaluation_params,
                    model=metric_config.get("model", "gpt-4"),
                    threshold=threshold,
                )

            # For other judges, pass threshold and model if provided
            kwargs = {}
            # Check both metric_config and top-level config for threshold/model
            if metric_config.get("threshold") is not None:
                kwargs["threshold"] = metric_config["threshold"]
            elif self.config.threshold is not None:
                kwargs["threshold"] = self.config.threshold

            if metric_config.get("model"):
                kwargs["model"] = metric_config["model"]
            elif self.config.model:
                kwargs["model"] = self.config.model

            return metric_class(**kwargs)

        except Exception as e:
            judge_type = self.config.deepeval_name
            raise JudgeError(
                f"Failed to create DeepEval metric '{judge_type}': {e} - "
                f"Check judge configuration and API credentials"
            ) from e

    async def evaluate(
        self, scenario: Scenario, subject_output: str
    ) -> JudgeResult:
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
            judge_id = self.config.id
            judge_type = self.config.deepeval_name
            run_id = get_current_run_id()
            if run_id:
                span.set_attribute("run_id", run_id)
            span.set_attribute("judge.id", judge_id)
            span.set_attribute("judge.name", judge_type)  # DeepEval metric name
            span.set_attribute("scenario.id", scenario.id)

            try:
                # Create DeepEval test case
                test_case = self._create_test_case(scenario, subject_output)

                # Run metric evaluation (synchronous in DeepEval, so run in executor)
                await asyncio.to_thread(self.metric.measure, test_case)

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

            except JudgeError:
                raise
            except Exception as e:
                raise JudgeError(
                    f"DeepEval evaluation failed for scenario '{scenario.id}': {e} - "
                    f"Check API credentials and judge configuration"
                ) from e

    def _create_test_case(
        self, scenario: Scenario, subject_output: str
    ) -> LLMTestCase:
        """
        Create DeepEval test case from scenario and output.

        Supports:
        - Standard expected output from scenario
        - expected_output_template with Jinja2 rendering for custom scenarios

        Args:
            scenario: The test scenario
            subject_output: The subject's output

        Returns:
            LLMTestCase instance
        """
        # Extract input text from scenario (support both dict and string formats)
        if isinstance(scenario.input, dict):
            input_text = scenario.input.get("text") or scenario.input.get(
                "query"
            ) or str(scenario.input)
        else:
            input_text = str(scenario.input)

        # Create test case with available data
        test_case_kwargs: Dict[str, Any] = {
            "input": input_text,
            "actual_output": subject_output,
        }

        # Determine expected output: template rendering takes precedence
        expected_output = self._get_expected_output(scenario)
        if expected_output:
            test_case_kwargs["expected_output"] = expected_output

        # Add context if available in scenario input (for dict format)
        if isinstance(scenario.input, dict) and "context" in scenario.input:
            test_case_kwargs["context"] = [scenario.input["context"]]

        # Add retrieval context if available (for dict format)
        if isinstance(scenario.input, dict) and "retrieval_context" in scenario.input:
            test_case_kwargs["retrieval_context"] = scenario.input[
                "retrieval_context"
            ]

        return LLMTestCase(**test_case_kwargs)

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

        # Fall back to scenario expected output
        return scenario.expected or scenario.expected_behavior or ""

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

        judge_type = self.config.deepeval_name
        return f"{judge_type} evaluation completed"
