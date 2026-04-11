"""
OneShot report generator.

Refactored to use the Unified Reporting Specification (Spec 4.1).
Treats OneShot as a conversation of length 1.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from gavel_ai.models.runtime import ReportData, ReporterConfig, ScenarioResult, Turn, VariantResult
from gavel_ai.reporters.jinja_reporter import Jinja2Reporter


class OneShotReporter(Jinja2Reporter):
    """
    OneShot-specific report generator using Unified Reporting Spec.

    Per Architecture Decision 8: Pluggable report formats with clean abstraction.
    Aligns with Unified Reporting Spec v1.0.
    """

    def __init__(self, config: ReporterConfig):
        """
        Initialize OneShotReporter with configuration.
        """
        super().__init__(config)

    def _build_context(self, run: Any) -> Dict[str, Any]:
        """
        Build context dictionary for OneShot template rendering.
        Converts OneShot results into the Unified ReportData format.
        """
        def get_val(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # Get run metadata
        run_id = get_val(run, "run_id", "unknown")
        title = get_val(run, "metadata", {}).get("eval_name", run_id)
        
        # Build scenarios mapping
        scenario_map: Dict[str, ScenarioResult] = {}
        
        # Extract results from run
        # results in Run are usually EvaluationResult objects
        results = get_val(run, "results", [])
        
        # summary_metrics: {variant: {metric: score}}
        summary_metrics: Dict[str, Dict[str, float]] = {}
        performance_metrics: Dict[str, Dict[str, float]] = {}

        # First pass: Initialize scenario map and aggregate metrics
        for result in results:
            def get_val(obj, key, default=None):
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)

            scenario_id = get_val(result, "scenario_id", "unknown")
            variant_id = get_val(result, "variant_id", "unknown")
            subject_id = get_val(result, "subject_id") or get_val(result, "test_subject", "default")
            
            if scenario_id not in scenario_map:
                scenario_map[scenario_id] = ScenarioResult(
                    scenario_id=scenario_id,
                    test_subject=subject_id,
                    system_input=str(get_val(result, "scenario_input", ""))
                )
            
            # Create VariantResult for this scenario
            processor_output = get_val(result, "processor_output", "")
            timing_ms = get_val(result, "timing_ms")
            if timing_ms is None:
                timing_ms = get_val(result, "metadata", {}).get("duration_ms", 0.0)

            timestamp = get_val(result, "timestamp")
            if not timestamp:
                timestamp = datetime.now().isoformat()

            # Map judgments
            judgments = []
            for j in get_val(result, "judges", []):
                j_id = get_val(j, "judge_id", "unknown")
                j_score = get_val(j, "score", 0)
                j_reasoning = get_val(j, "reasoning", "")
                j_evidence = get_val(j, "evidence", "")

                judgments.append({
                    "judge_id": j_id,
                    "score": j_score,
                    "reasoning": j_reasoning,
                    "evidence": j_evidence
                })
                
                # Update summary_metrics
                if variant_id not in summary_metrics:
                    summary_metrics[variant_id] = {}
                
                metric_name = j_id
                if metric_name not in summary_metrics[variant_id]:
                    summary_metrics[variant_id][metric_name] = 0.0
                
                summary_metrics[variant_id][metric_name] += float(j_score)

            # Build turns: OneShot is a 1-turn conversation (user input → assistant output)
            turns = []
            scenario_input_str = str(get_val(result, "scenario_input", "") or "")
            if scenario_input_str:
                turns.append(Turn(role="user", content=scenario_input_str))
            if processor_output:
                turns.append(Turn(
                    role="assistant",
                    content=str(processor_output),
                    duration_ms=float(timing_ms or 0.0),
                ))

            variant_result = VariantResult(
                variant_id=variant_id,
                turns=turns,
                output=str(processor_output),
                judgments=judgments,
                metrics={},
                timing={"total_time": float(timing_ms or 0.0) / 1000.0}
            )
            
            # Store in map
            scenario_map[scenario_id].variants[variant_id] = variant_result

        # Calculate averages for summary_metrics
        variant_scenario_counts: Dict[str, int] = {}
        for result in results:
            vid = get_val(result, "variant_id", "unknown")
            variant_scenario_counts[vid] = variant_scenario_counts.get(vid, 0) + 1

        for variant, metrics in summary_metrics.items():
            count = variant_scenario_counts.get(variant, 1)
            for mname in metrics:
                metrics[mname] /= count

        # Populate performance_metrics
        for variant, count in variant_scenario_counts.items():
            total_timing = 0.0
            for scenario in scenario_map.values():
                if variant in scenario.variants:
                    total_timing += scenario.variants[variant].timing.get("total_time", 0.0)
            
            performance_metrics[variant] = {
                "avg_turn_time": total_timing / count if count > 0 else 0.0,
                "total_time": total_timing
            }

        # Build scenarios_by_subject
        scenarios_by_subject: Dict[str, List[ScenarioResult]] = {}
        for scenario in scenario_map.values():
            subj = scenario.test_subject or "default"
            if subj not in scenarios_by_subject:
                scenarios_by_subject[subj] = []
            scenarios_by_subject[subj].append(scenario)

        # Create ReportData object
        report_data = ReportData(
            title=title,
            run_id=run_id,
            generated_at=datetime.now(),
            summary_metrics=summary_metrics,
            performance_metrics=performance_metrics,
            scenarios=list(scenario_map.values()),
            scenarios_by_subject=scenarios_by_subject
        )
        
        # Return as dict for Jinja2
        return report_data.model_dump()
