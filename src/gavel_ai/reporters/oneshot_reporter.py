"""
OneShot report generator.

Refactored to use the Unified Reporting Specification (Spec 4.1).
Treats OneShot as a conversation of length 1.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

INPUT_COLLAPSE_THRESHOLD: int = 200
RESPONSE_TRUNCATE_THRESHOLD: int = 500

from gavel_ai.models.runtime import (
    DeterministicRunResult,
    ReportData,
    ReporterConfig,
    ScenarioResult,
    Turn,
    VariantResult,
)
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
        def get_val(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # Get run metadata
        run_id = get_val(run, "run_id", "unknown")
        title = get_val(run, "metadata", {}).get("eval_name", run_id)

        # Build error set from raw_results: (scenario_id, variant_id) → has error
        error_set: Set[Tuple[str, str]] = set()
        raw_results = getattr(run, "raw_results", None) or []
        for raw in raw_results:
            sid = raw.get("scenario_id") if isinstance(raw, dict) else getattr(raw, "scenario_id", None)
            vid = raw.get("variant_id") if isinstance(raw, dict) else getattr(raw, "variant_id", None)
            err = raw.get("error") if isinstance(raw, dict) else getattr(raw, "error", None)
            if sid and vid and err is not None:
                error_set.add((sid, vid))

        # Build scenarios mapping
        scenario_map: Dict[str, ScenarioResult] = {}

        # Extract results from run
        results = get_val(run, "results", [])

        # score accumulators: {variant: {judge: sum}}, {variant: {judge: count}}, {variant: {judge: skipped}}
        judge_sums: Dict[str, Dict[str, float]] = {}
        judge_counts: Dict[str, Dict[str, int]] = {}
        skipped_counts: Dict[str, Dict[str, int]] = {}
        performance_metrics: Dict[str, Dict[str, float]] = {}

        # First pass: build scenario map and accumulate judge scores
        for result in results:
            def get_val(obj: Any, key: str, default: Any = None) -> Any:  # noqa: F811
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

            # Determine if this (scenario, variant) had a processor error
            is_error = (scenario_id, variant_id) in error_set

            # Map judgments and accumulate scores
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

                if not is_error:
                    # Accumulate score
                    if variant_id not in judge_sums:
                        judge_sums[variant_id] = {}
                    judge_sums[variant_id][j_id] = judge_sums[variant_id].get(j_id, 0.0) + float(j_score)
                    if variant_id not in judge_counts:
                        judge_counts[variant_id] = {}
                    judge_counts[variant_id][j_id] = judge_counts[variant_id].get(j_id, 0) + 1
                else:
                    # Track skip
                    if variant_id not in skipped_counts:
                        skipped_counts[variant_id] = {}
                    skipped_counts[variant_id][j_id] = skipped_counts[variant_id].get(j_id, 0) + 1

            # Build turns: OneShot is a 1-turn conversation
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

            scenario_map[scenario_id].variants[variant_id] = variant_result

        # Calculate averages for summary_metrics (per-judge count, excluding errors)
        summary_metrics: Dict[str, Dict[str, float]] = {}
        for variant_id, j_sums in judge_sums.items():
            summary_metrics[variant_id] = {}
            for j_id, total in j_sums.items():
                count = judge_counts.get(variant_id, {}).get(j_id, 1)
                summary_metrics[variant_id][j_id] = total / count if count > 0 else 0.0

        # Populate performance_metrics
        variant_scenario_counts: Dict[str, int] = {}
        for result in results:
            vid = get_val(result, "variant_id", "unknown")
            variant_scenario_counts[vid] = variant_scenario_counts.get(vid, 0) + 1

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

        # Build deterministic_results from run.deterministic_metrics
        det_results: List[DeterministicRunResult] = []
        det_metrics = getattr(run, "deterministic_metrics", None)
        if det_metrics:
            for v in det_metrics.values():
                if isinstance(v, DeterministicRunResult):
                    det_results.append(v)
                elif isinstance(v, dict):
                    det_results.append(DeterministicRunResult(**v))

        # Create ReportData object
        report_data = ReportData(
            title=title,
            run_id=run_id,
            generated_at=datetime.now(),
            summary_metrics=summary_metrics,
            performance_metrics=performance_metrics,
            scenarios=list(scenario_map.values()),
            scenarios_by_subject=scenarios_by_subject,
            deterministic_results=det_results,
        )

        # Return as dict for Jinja2, with extra skipped_counts key
        ctx = report_data.model_dump()
        ctx["skipped_counts"] = skipped_counts

        # New context keys for upgraded report template
        telemetry = getattr(run, "telemetry", None)
        ctx["total_execution_time_s"] = (
            telemetry.get("total_duration_seconds") if isinstance(telemetry, dict) else None
        )

        run_metadata: Dict[str, Any] = getattr(run, "metadata", {}) or {}
        ctx["input_source"] = run_metadata.get("input_source", "")
        ctx["scenario_count"] = run_metadata.get("scenario_count", 0)

        # subject_names: prefer metadata, fall back to unique subjects from scenario map
        subject_names: List[str] = run_metadata.get("subject_names", [])
        if not subject_names:
            seen: set = set()
            subject_names = []
            for scenario in scenario_map.values():
                subj: str = scenario.test_subject or "default"
                if subj not in seen:
                    seen.add(subj)
                    subject_names.append(subj)
        ctx["subject_names"] = subject_names

        ctx["input_collapse_threshold"] = INPUT_COLLAPSE_THRESHOLD
        ctx["response_truncate_threshold"] = RESPONSE_TRUNCATE_THRESHOLD

        return ctx
