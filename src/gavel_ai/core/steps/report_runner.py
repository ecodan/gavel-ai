"""
Report runner step for OneShot workflow.

Responsibilities:
- Export results_raw.jsonl (immutable processor outputs)
- Export results_judged.jsonl (judge evaluations)
- Generate manifest.json with config hash
- Compute and save run_metadata.json
- Generate report.html via OneShotReporter

Per Tech Spec 3.9: Extracted from run() lines 320-444.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.base import (
    DEFAULT_EVAL_ROOT,
    Step,
    StepPhase,
)
from gavel_ai.models.runtime import ReporterConfig
from gavel_ai.reporters.oneshot_reporter import OneShotReporter
from gavel_ai.storage.results_exporter import ResultsExporter
from gavel_ai.telemetry import get_metadata_collector


@dataclass
class RunData:
    """Data object for reporter - holds run metadata and results."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    results: List[Dict[str, Any]] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)


class ReportRunnerStep(Step):
    """
    Exports results and generates reports.

    Sets context.report_content with generated report.
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize report runner step.

        Args:
            logger: Logger for step execution
        """
        super().__init__(logger)

    @property
    def phase(self) -> StepPhase:
        return StepPhase.REPORTING

    async def execute(self, run_context: RunContext) -> None:
        """
        Export results and generate report.

        Args:
            run_context: RunContext with processor_results and evaluation_results

        Raises:
            ConfigError: If required data is missing
        """
        eval_config = run_context.eval_context.eval_config.read()
        scenarios = run_context.eval_context.scenarios.read()
        processor_results = run_context.processor_results
        evaluation_results = run_context.evaluation_results or []

        if processor_results is None:
            raise ConfigError(
                "ReportRunnerStep requires processor_results - Run ScenarioProcessorStep first"
            )

        test_subject: str = run_context.test_subject or "unknown"
        model_variant: str = run_context.model_variant or "unknown"
        run_dir: Path = run_context.run_dir

        # Derive processor type from test_subject_type
        processor_type: str = (
            "prompt_input" if eval_config.test_subject_type == "local" else "closedbox_input"
        )

        self.logger.info("Exporting results and generating report")

        # 1. Export raw processor results
        exporter = ResultsExporter(run_dir, processor_type=processor_type)

        self.logger.debug(
            f"Exporting {len(processor_results)} processor results to results_raw.jsonl"
        )
        exporter.export_raw_results(
            scenarios,
            processor_results,
            test_subject=test_subject,
            variant_id=model_variant,
        )

        # 2. Export judged results
        self.logger.debug(
            f"Exporting {len(processor_results)} judged results to results_judged.jsonl"
        )
        exporter.export_judged_results(
            scenarios=scenarios,
            processor_results=processor_results,
            judge_evaluations=evaluation_results,
            test_subject=test_subject,
            variant_id=model_variant,
        )

        # Get start time from metadata collector for duration calculation
        metadata_collector = get_metadata_collector()
        start_time_epoch = metadata_collector.run_start_time or time.time()

        # 3. Generate manifest.json
        manifest_file = run_dir / "manifest.json"
        try:
            config_files_for_hash: Dict[str, Path] = {
                "agents": run_dir / ".config" / "agents.json",
                "eval_config": run_dir / ".config" / "eval_config.json",
            }

            scenarios_path = run_dir / ".config" / "scenarios.json"
            if scenarios_path.exists():
                config_files_for_hash["scenarios"] = scenarios_path
            else:
                alt_scenarios = (
                    Path(DEFAULT_EVAL_ROOT)
                    / run_context.eval_context.eval_name
                    / "data"
                    / "scenarios.json"
                )
                if alt_scenarios.exists():
                    config_files_for_hash["scenarios"] = alt_scenarios

            config_hash: str = (
                exporter.compute_config_hash(config_files_for_hash)
                if len(config_files_for_hash) >= 2
                else "unknown"
            )

            failed_count = sum(1 for pr in processor_results if pr.error is not None)
            status: str = (
                "completed"
                if failed_count == 0
                else "partial"
                if failed_count < len(processor_results)
                else "failed"
            )

            # Count judges from test_subjects
            judge_count = 0
            if eval_config.test_subjects:
                for subject in eval_config.test_subjects:
                    if subject.judges:
                        judge_count += len(subject.judges)

            timestamp = datetime.now(timezone.utc).isoformat()
            manifest_data: Dict[str, Any] = {
                "timestamp": timestamp,
                "run_id": run_context.run_id,
                "eval_name": run_context.eval_context.eval_name,
                "config_hash": config_hash,
                "scenario_count": len(scenarios),
                "variant_count": 1,
                "judge_count": judge_count,
                "processor_type": processor_type,
                "status": status,
                "completed_count": len(scenarios) - failed_count,
                "failed_count": failed_count,
                "duration_seconds": time.time() - start_time_epoch,
            }

            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

            self.logger.debug(f"Manifest saved to {manifest_file}")
        except FileNotFoundError as e:
            self.logger.warning(f"Could not compute config hash: {e}")
            timestamp = datetime.now(timezone.utc).isoformat()
            config_hash = "unknown"

        # 4. Record run end and compute metadata
        self.logger.debug("Computing run metadata statistics")
        metadata_collector.record_run_end()
        run_metadata_stats = metadata_collector.compute_statistics(
            run_id=run_context.run_id,
            eval_name=run_context.eval_context.eval_name,
        )

        metadata_file = run_dir / "run_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(run_metadata_stats.model_dump_json(indent=2))

        self.logger.debug(f"Run metadata saved to {metadata_file}")

        # 5. Generate report
        report_path = run_dir / "report.html"
        templates_dir = Path(__file__).parent.parent.parent / "reporters" / "templates"
        reporter_config = ReporterConfig(
            template_path=str(templates_dir),
            output_format="html",
        )
        reporter = OneShotReporter(reporter_config)

        # Create run data object for reporter
        run_data = RunData(
            metadata={
                "eval_name": run_context.eval_context.eval_name,
                "timestamp": timestamp,
                "config_hash": config_hash,
                "scenario_count": len(scenarios),
                "variant_count": 1,
                "eval_type": "oneshot",
            },
            results=evaluation_results,
            telemetry={
                "total_duration_seconds": run_metadata_stats.total_duration_seconds,
                "llm_calls": run_metadata_stats.llm_calls.model_dump(),
            },
        )

        self.logger.debug(f"Generating report to {report_path}")
        report_content = await reporter.generate(run_data, "oneshot.html")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        self.logger.debug(f"Report generated: {report_path}")

        duration: float = time.time() - start_time_epoch
        self.logger.info(f"Report generated in {duration:.2f}s: {report_path}")
