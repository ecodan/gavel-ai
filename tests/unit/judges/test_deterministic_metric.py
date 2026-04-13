"""
Unit tests for DeterministicMetric, ClassifierMetric, and RegressionMetric.
"""

import json
import pytest
from unittest.mock import MagicMock

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.judges.deterministic_metric import ClassifierMetric, RegressionMetric
from gavel_ai.judges.judge_registry import JudgeRegistry
from gavel_ai.models.config import JudgeConfig
from gavel_ai.models.runtime import Scenario


pytestmark = pytest.mark.unit


def make_classifier_config(**kwargs) -> JudgeConfig:
    cfg = {
        "prediction_field": "label",
        "actual_field": "expected",
        "report_metric": "accuracy",
    }
    cfg.update(kwargs)
    return JudgeConfig(name="test_classifier", type="classifier", config=cfg)


def make_regression_config(**kwargs) -> JudgeConfig:
    cfg = {
        "prediction_field": "value",
        "actual_field": "expected",
        "report_metric": "mean_absolute_error",
    }
    cfg.update(kwargs)
    return JudgeConfig(name="test_regression", type="regression", config=cfg)


def make_scenario(sid: str, input_data: dict) -> Scenario:
    return Scenario(id=sid, input=input_data)


class TestClassifierMetric:
    def test_match_true(self):
        metric = ClassifierMetric(make_classifier_config())
        scenario = make_scenario("s1", {"expected": "positive"})
        result = metric.evaluate_sample("s1", json.dumps({"label": "positive"}), scenario)
        assert result.match is True
        assert result.prediction == "positive"
        assert result.actual == "positive"
        assert result.skip_reason is None

    def test_match_false(self):
        metric = ClassifierMetric(make_classifier_config())
        scenario = make_scenario("s1", {"expected": "positive"})
        result = metric.evaluate_sample("s1", json.dumps({"label": "negative"}), scenario)
        assert result.match is False
        assert result.raw_score is None
        assert result.skip_reason is None

    def test_case_insensitive(self):
        metric = ClassifierMetric(make_classifier_config())
        scenario = make_scenario("s1", {"expected": "Positive"})
        result = metric.evaluate_sample("s1", json.dumps({"label": "POSITIVE"}), scenario)
        assert result.match is True

    def test_skip_non_json_output(self):
        metric = ClassifierMetric(make_classifier_config())
        scenario = make_scenario("s1", {"expected": "positive"})
        result = metric.evaluate_sample("s1", "not json at all", scenario)
        assert result.skip_reason == "outputs is not a dict"
        assert result.match is None
        assert result.raw_score is None

    def test_skip_missing_prediction_field(self):
        metric = ClassifierMetric(make_classifier_config())
        scenario = make_scenario("s1", {"expected": "positive"})
        result = metric.evaluate_sample("s1", json.dumps({"other_field": "x"}), scenario)
        assert result.skip_reason == "prediction_field not found: label"

    def test_skip_missing_actual_field(self):
        metric = ClassifierMetric(make_classifier_config())
        scenario = make_scenario("s1", {"wrong_key": "positive"})
        result = metric.evaluate_sample("s1", json.dumps({"label": "positive"}), scenario)
        assert result.skip_reason == "actual_field not found: expected"

    def test_population_score_none_when_all_skipped(self):
        metric = ClassifierMetric(make_classifier_config())
        scenario = make_scenario("s1", {})
        metric.evaluate_sample("s1", "bad", scenario)
        metric.evaluate_sample("s2", "bad", scenario)
        result = metric.compute()
        assert result.population_score is None

    def test_accuracy_three_samples(self):
        metric = ClassifierMetric(make_classifier_config())
        scenarios = [
            make_scenario("s1", {"expected": "pos"}),
            make_scenario("s2", {"expected": "neg"}),
            make_scenario("s3", {"expected": "pos"}),
        ]
        outputs = [
            json.dumps({"label": "pos"}),   # correct
            json.dumps({"label": "neg"}),   # correct
            json.dumps({"label": "neg"}),   # wrong
        ]
        for sid, out, scen in zip(["s1", "s2", "s3"], outputs, scenarios):
            metric.evaluate_sample(sid, out, scen)
        result = metric.compute()
        assert result.population_score == pytest.approx(2 / 3, abs=0.001)

    def test_fbeta_missing_beta_raises(self):
        with pytest.raises(ConfigError, match="beta"):
            ClassifierMetric(make_classifier_config(report_metric="fbeta"))

    def test_fbeta_with_beta_succeeds(self):
        metric = ClassifierMetric(make_classifier_config(report_metric="fbeta", beta=1.0))
        scenario = make_scenario("s1", {"expected": "pos"})
        metric.evaluate_sample("s1", json.dumps({"label": "pos"}), scenario)
        result = metric.compute()
        assert result.population_score is not None


class TestRegressionMetric:
    def test_signed_error_positive(self):
        metric = RegressionMetric(make_regression_config())
        scenario = make_scenario("s1", {"expected": "2.0"})
        result = metric.evaluate_sample("s1", json.dumps({"value": 3.5}), scenario)
        assert result.raw_score == pytest.approx(1.5)
        assert result.match is None
        assert result.skip_reason is None

    def test_signed_error_negative(self):
        metric = RegressionMetric(make_regression_config())
        scenario = make_scenario("s1", {"expected": "5.0"})
        result = metric.evaluate_sample("s1", json.dumps({"value": 3.0}), scenario)
        assert result.raw_score == pytest.approx(-2.0)

    def test_skip_non_json_output(self):
        metric = RegressionMetric(make_regression_config())
        scenario = make_scenario("s1", {"expected": "2.0"})
        result = metric.evaluate_sample("s1", "not json", scenario)
        assert result.skip_reason == "outputs is not a dict"

    def test_skip_missing_prediction_field(self):
        metric = RegressionMetric(make_regression_config())
        scenario = make_scenario("s1", {"expected": "2.0"})
        result = metric.evaluate_sample("s1", json.dumps({"other": 1.0}), scenario)
        assert result.skip_reason == "prediction_field not found: value"

    def test_skip_missing_actual_field(self):
        metric = RegressionMetric(make_regression_config())
        scenario = make_scenario("s1", {"wrong_key": "2.0"})
        result = metric.evaluate_sample("s1", json.dumps({"value": 3.0}), scenario)
        assert result.skip_reason == "actual_field not found: expected"

    def test_population_score_none_when_all_skipped(self):
        metric = RegressionMetric(make_regression_config())
        scenario = make_scenario("s1", {})
        metric.evaluate_sample("s1", "bad", scenario)
        result = metric.compute()
        assert result.population_score is None

    def test_mean_absolute_error_fixture(self):
        metric = RegressionMetric(make_regression_config())
        samples = [
            ("s1", {"expected": "1.0"}, {"value": 2.0}),   # error=1.0
            ("s2", {"expected": "3.0"}, {"value": 3.0}),   # error=0.0
            ("s3", {"expected": "2.0"}, {"value": 4.0}),   # error=2.0
        ]
        for sid, inp, out in samples:
            metric.evaluate_sample(sid, json.dumps(out), make_scenario(sid, inp))
        result = metric.compute()
        # MAE = (1.0 + 0.0 + 2.0) / 3 = 1.0
        assert result.population_score == pytest.approx(1.0)


class TestJudgeRegistryIntegration:
    def test_registry_returns_classifier(self):
        config = make_classifier_config()
        instance = JudgeRegistry.create(config)
        assert isinstance(instance, ClassifierMetric)

    def test_registry_returns_regression(self):
        config = make_regression_config()
        instance = JudgeRegistry.create(config)
        assert isinstance(instance, RegressionMetric)
