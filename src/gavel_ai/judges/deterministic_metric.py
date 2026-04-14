"""
Deterministic metric judges for gavel-ai.

Provides scikit-learn-backed evaluation metrics that operate on
structured processor outputs without an LLM judge call.

Includes:
- DeterministicMetric (ABC): base class
- ClassifierMetric: case-insensitive label matching + sklearn classification metrics
- RegressionMetric: unbounded signed error + sklearn regression metrics

Registered as "classifier" and "regression" in JudgeRegistry.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.models.config import JudgeConfig
from gavel_ai.models.runtime import DeterministicRunResult, PerSampleDeterministicResult, Scenario

logger = logging.getLogger("gavel-ai")

SKLEARN_METRIC_REGISTRY: Dict[str, Any] = {}

try:
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        fbeta_score,
        mean_absolute_error,
        mean_squared_error,
        r2_score,
    )
    SKLEARN_METRIC_REGISTRY = {
        "accuracy": lambda y_true, y_pred, **kw: accuracy_score(y_true, y_pred),
        "f1": lambda y_true, y_pred, **kw: f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "fbeta": lambda y_true, y_pred, beta=1.0, **kw: fbeta_score(y_true, y_pred, beta=beta, average="weighted", zero_division=0),
        "mean_absolute_error": lambda y_true, y_pred, **kw: mean_absolute_error(y_true, y_pred),
        "mean_squared_error": lambda y_true, y_pred, **kw: mean_squared_error(y_true, y_pred),
        "r2_score": lambda y_true, y_pred, **kw: r2_score(y_true, y_pred),
    }
except ImportError:
    pass  # scikit-learn not installed; will raise at use time


def _resolve_path(obj: Any, dotted_key: str) -> Any:
    """
    Navigate a nested dict using a dotted-path key (e.g. "result.label").

    Raises:
        KeyError: If any key in the path is absent.
    """
    parts = dotted_key.split(".")
    current: Any = obj
    for part in parts:
        if isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(part)
    return current


class DeterministicMetric(ABC):
    """
    Abstract base class for deterministic (non-LLM) evaluation metrics.

    Subclasses implement evaluate_sample() for per-record scoring and
    compute() to aggregate into a population metric using scikit-learn.
    """

    def __init__(self, config: JudgeConfig) -> None:
        self.config: JudgeConfig = config
        self.name: str = config.name
        self.judge_type: str = config.type
        cfg: Dict[str, Any] = config.config or {}
        self.prediction_field: str = cfg.get("prediction_field", "prediction")
        self.actual_field: str = cfg.get("actual_field", "actual")
        self.report_metric: str = cfg.get("report_metric", "accuracy")
        self._samples: List[PerSampleDeterministicResult] = []

    @abstractmethod
    def evaluate_sample(
        self,
        scenario_id: str,
        processor_output: str,
        scenario: Scenario,
    ) -> PerSampleDeterministicResult:
        """
        Evaluate a single sample.

        Args:
            scenario_id: Identifier of the scenario being evaluated.
            processor_output: Raw string output from the processor/model.
            scenario: The scenario providing ground-truth values.

        Returns:
            PerSampleDeterministicResult (skip_reason set when skipped).
        """

    @abstractmethod
    def compute(self) -> DeterministicRunResult:
        """
        Aggregate accumulated samples into a population metric.

        Returns:
            DeterministicRunResult with population_score=None when all skipped.
        """

    def _parse_output(self, processor_output: str) -> Optional[Dict[str, Any]]:
        """Parse processor_output as JSON dict; return None on failure."""
        try:
            parsed = json.loads(processor_output)
            if isinstance(parsed, dict):
                return parsed
            return None
        except (json.JSONDecodeError, TypeError):
            return None

    def _resolve_actual(self, scenario: Scenario) -> Optional[Any]:
        """
        Resolve actual value from scenario using actual_field path.

        Checks scenario.input (if dict) first, then scenario.model_dump().
        Returns None if not found.
        """
        # Try scenario.input dict first
        if isinstance(scenario.input, dict):
            try:
                return _resolve_path(scenario.input, self.actual_field)
            except KeyError:
                pass
        # Fall back to full scenario dict
        try:
            return _resolve_path(scenario.model_dump(), self.actual_field)
        except KeyError:
            return None


class ClassifierMetric(DeterministicMetric):
    """
    Deterministic classifier metric.

    Extracts a label prediction from JSON processor output,
    compares case-insensitively against the actual label from the scenario,
    and computes a population metric (e.g. accuracy, f1, fbeta) via scikit-learn.
    """

    def __init__(self, config: JudgeConfig) -> None:
        super().__init__(config)
        cfg: Dict[str, Any] = config.config or {}
        if self.report_metric == "fbeta" and "beta" not in cfg:
            raise ConfigError(
                f"ClassifierMetric '{self.name}': report_metric='fbeta' requires 'beta' in config - "
                "Add 'beta' field to judge config"
            )
        self.beta: float = float(cfg.get("beta", 1.0))
        self._y_true: List[str] = []
        self._y_pred: List[str] = []

    def evaluate_sample(
        self,
        scenario_id: str,
        processor_output: str,
        scenario: Scenario,
    ) -> PerSampleDeterministicResult:
        parsed = self._parse_output(processor_output)
        if parsed is None:
            result = PerSampleDeterministicResult(
                scenario_id=scenario_id,
                skip_reason="outputs is not a dict",
            )
            self._samples.append(result)
            return result

        # Extract prediction
        try:
            prediction = str(_resolve_path(parsed, self.prediction_field))
        except KeyError:
            result = PerSampleDeterministicResult(
                scenario_id=scenario_id,
                skip_reason=f"prediction_field not found: {self.prediction_field}",
            )
            self._samples.append(result)
            return result

        # Extract actual
        actual_value = self._resolve_actual(scenario)
        if actual_value is None:
            result = PerSampleDeterministicResult(
                scenario_id=scenario_id,
                prediction=prediction,
                skip_reason=f"actual_field not found: {self.actual_field}",
            )
            self._samples.append(result)
            return result

        actual = str(actual_value)
        match = prediction.strip().lower() == actual.strip().lower()

        self._y_true.append(actual)
        self._y_pred.append(prediction)

        result = PerSampleDeterministicResult(
            scenario_id=scenario_id,
            prediction=prediction,
            actual=actual,
            match=match,
        )
        self._samples.append(result)
        return result

    def compute(self) -> DeterministicRunResult:
        population_score: Optional[float] = None
        if self._y_true:
            metric_fn = SKLEARN_METRIC_REGISTRY.get(self.report_metric)
            if metric_fn is None:
                raise ConfigError(
                    f"ClassifierMetric '{self.name}': unknown report_metric '{self.report_metric}' - "
                    f"Available: {list(SKLEARN_METRIC_REGISTRY.keys())}"
                )
            population_score = float(metric_fn(self._y_true, self._y_pred, beta=self.beta))

        return DeterministicRunResult(
            metric_name=self.name,
            judge_type=self.judge_type,
            report_metric=self.report_metric,
            population_score=population_score,
            samples=list(self._samples),
        )


class RegressionMetric(DeterministicMetric):
    """
    Deterministic regression metric.

    Extracts a numeric prediction from JSON processor output,
    computes unbounded signed error (prediction − actual),
    and aggregates via scikit-learn regression metric.
    """

    def __init__(self, config: JudgeConfig) -> None:
        super().__init__(config)
        self._y_true: List[float] = []
        self._y_pred: List[float] = []

    def evaluate_sample(
        self,
        scenario_id: str,
        processor_output: str,
        scenario: Scenario,
    ) -> PerSampleDeterministicResult:
        parsed = self._parse_output(processor_output)
        if parsed is None:
            result = PerSampleDeterministicResult(
                scenario_id=scenario_id,
                skip_reason="outputs is not a dict",
            )
            self._samples.append(result)
            return result

        # Extract prediction
        try:
            prediction_raw = _resolve_path(parsed, self.prediction_field)
            prediction_val = float(prediction_raw)
        except KeyError:
            result = PerSampleDeterministicResult(
                scenario_id=scenario_id,
                skip_reason=f"prediction_field not found: {self.prediction_field}",
            )
            self._samples.append(result)
            return result
        except (TypeError, ValueError):
            result = PerSampleDeterministicResult(
                scenario_id=scenario_id,
                skip_reason=f"prediction_field not found: {self.prediction_field}",
            )
            self._samples.append(result)
            return result

        # Extract actual
        actual_value = self._resolve_actual(scenario)
        if actual_value is None:
            result = PerSampleDeterministicResult(
                scenario_id=scenario_id,
                prediction=str(prediction_val),
                skip_reason=f"actual_field not found: {self.actual_field}",
            )
            self._samples.append(result)
            return result

        try:
            actual_val = float(actual_value)
        except (TypeError, ValueError):
            result = PerSampleDeterministicResult(
                scenario_id=scenario_id,
                prediction=str(prediction_val),
                skip_reason=f"actual_field not found: {self.actual_field}",
            )
            self._samples.append(result)
            return result

        raw_score = prediction_val - actual_val

        self._y_true.append(actual_val)
        self._y_pred.append(prediction_val)

        result = PerSampleDeterministicResult(
            scenario_id=scenario_id,
            prediction=str(prediction_val),
            actual=str(actual_val),
            raw_score=raw_score,
        )
        self._samples.append(result)
        return result

    def compute(self) -> DeterministicRunResult:
        population_score: Optional[float] = None
        if self._y_true:
            metric_fn = SKLEARN_METRIC_REGISTRY.get(self.report_metric)
            if metric_fn is None:
                raise ConfigError(
                    f"RegressionMetric '{self.name}': unknown report_metric '{self.report_metric}' - "
                    f"Available: {list(SKLEARN_METRIC_REGISTRY.keys())}"
                )
            population_score = float(metric_fn(self._y_true, self._y_pred))

        return DeterministicRunResult(
            metric_name=self.name,
            judge_type=self.judge_type,
            report_metric=self.report_metric,
            population_score=population_score,
            samples=list(self._samples),
        )


# Module-level registration
from gavel_ai.judges.judge_registry import JudgeRegistry  # noqa: E402

JudgeRegistry.register("classifier", ClassifierMetric)
JudgeRegistry.register("regression", RegressionMetric)
