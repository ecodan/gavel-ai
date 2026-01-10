"""Results export functionality for JSONL files.

Exports processor outputs and judge evaluations to:
- results_raw.jsonl (immutable processor execution records)
- results_judged.jsonl (mutable judge evaluation results)

Per Architecture Decision 4: Flat JSONL schema with scenario/variant/processor dimensions.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import jsonlines

from gavel_ai.core.models import ProcessorResult, Scenario
from gavel_ai.log_config import get_application_logger

logger = get_application_logger()


class ResultsExporter:
    """Export processor and judge results to JSONL files."""

    def __init__(self, run_dir: Path, processor_type: str = "prompt_input"):
        """
        Initialize exporter.

        Args:
            run_dir: Path to run directory
            processor_type: Type of processor (implementation detail, not persisted in results)
        """
        self.run_dir = run_dir
        self.processor_type = processor_type

    def export_raw_results(
        self,
        scenarios: List[Scenario],
        processor_results: List[ProcessorResult],
        test_subject: str = "unknown",
        variant_id: str = "default",
    ) -> Path:
        """
        Export processor outputs to results_raw.jsonl.

        Creates immutable record of processor execution.

        Args:
            scenarios: List of Scenario instances processed
            processor_results: List of ProcessorResult from execution
            test_subject: Prompt/system under test name (e.g., "assistant:v1")
            variant_id: Model or parameter variant (e.g., "claude-sonnet", "temperature-0.7")

        Returns:
            Path to created results_raw.jsonl file

        Raises:
            ValueError: If scenarios and processor_results have different lengths
        """
        if len(scenarios) != len(processor_results):
            raise ValueError(
                f"Scenario count ({len(scenarios)}) must match "
                f"processor result count ({len(processor_results)})"
            )

        results_file = self.run_dir / "results_raw.jsonl"
        timestamp = datetime.now(timezone.utc).isoformat()

        raw_entries = []
        for scenario, proc_result in zip(scenarios, processor_results):
            # Extract timing and token data from processor metadata
            metadata = proc_result.metadata or {}
            timing_ms = metadata.get("latency_ms", 0)
            tokens_info = metadata.get("tokens", {})
            tokens_prompt = tokens_info.get("prompt", 0) if isinstance(tokens_info, dict) else 0
            tokens_completion = (
                tokens_info.get("completion", 0) if isinstance(tokens_info, dict) else 0
            )

            entry = {
                "test_subject": test_subject,
                "variant_id": variant_id,
                "scenario_id": scenario.id,
                "processor_output": str(proc_result.output),
                "timing_ms": int(timing_ms),
                "tokens_prompt": int(tokens_prompt),
                "tokens_completion": int(tokens_completion),
                "error": proc_result.error,
                "timestamp": timestamp,
            }
            raw_entries.append(entry)

        # Write JSONL file
        with jsonlines.open(results_file, mode="w") as writer:
            writer.write_all(raw_entries)

        logger.info(f"Exported {len(raw_entries)} raw results to {results_file}")
        return results_file

    def export_judged_results(
        self,
        scenarios: List[Scenario],
        processor_results: List[ProcessorResult],
        judge_evaluations: List[Dict[str, Any]],
        test_subject: str = "unknown",
        variant_id: str = "default",
    ) -> Path:
        """
        Export processor outputs + judge evaluations to results_judged.jsonl.

        Creates mutable judgment layer combining processor output with judge scores.

        Args:
            scenarios: List of Scenario instances processed
            processor_results: List of ProcessorResult from execution
            judge_evaluations: List of evaluation results with judge data
            test_subject: Prompt/system under test name (e.g., "assistant:v1")
            variant_id: Model or parameter variant (e.g., "claude-sonnet", "temperature-0.7")

        Returns:
            Path to created results_judged.jsonl file

        Raises:
            ValueError: If counts don't match
        """
        if len(scenarios) != len(processor_results):
            raise ValueError(
                f"Scenario count ({len(scenarios)}) must match "
                f"processor result count ({len(processor_results)})"
            )

        if judge_evaluations and len(scenarios) != len(judge_evaluations):
            raise ValueError(
                f"Scenario count ({len(scenarios)}) must match "
                f"evaluation result count ({len(judge_evaluations)})"
            )

        results_file = self.run_dir / "results_judged.jsonl"
        timestamp = datetime.now(timezone.utc).isoformat()

        judged_entries = []
        for idx, (scenario, proc_result) in enumerate(zip(scenarios, processor_results)):
            # Extract timing and token data from processor metadata
            metadata = proc_result.metadata or {}
            timing_ms = metadata.get("latency_ms", 0)
            tokens_info = metadata.get("tokens", {})
            tokens_prompt = tokens_info.get("prompt", 0) if isinstance(tokens_info, dict) else 0
            tokens_completion = (
                tokens_info.get("completion", 0) if isinstance(tokens_info, dict) else 0
            )

            # Base entry with processor data (same schema as results_raw.jsonl)
            entry = {
                "test_subject": test_subject,
                "variant_id": variant_id,
                "scenario_id": scenario.id,
                "processor_output": str(proc_result.output),
                "timing_ms": int(timing_ms),
                "tokens_prompt": int(tokens_prompt),
                "tokens_completion": int(tokens_completion),
                "error": proc_result.error,
                "timestamp": timestamp,
                "judges": [],  # Initialize empty judges array
            }

            # Add judge evaluations if available
            if judge_evaluations and idx < len(judge_evaluations):
                eval_result = judge_evaluations[idx]
                judges_data = eval_result.get("judges", [])
                entry["judges"] = judges_data

            judged_entries.append(entry)

        # Write JSONL file
        with jsonlines.open(results_file, mode="w") as writer:
            writer.write_all(judged_entries)

        logger.info(f"Exported {len(judged_entries)} judged results to {results_file}")
        return results_file

    @staticmethod
    def compute_config_hash(config_files: Dict[str, Path]) -> str:
        """
        Compute SHA256 hash of configuration files.

        For reproducibility verification.

        Args:
            config_files: Dict mapping config name to Path
                (e.g., {"agents": Path(...), "eval_config": Path(...), ...})

        Returns:
            SHA256 hash as hex string

        Raises:
            FileNotFoundError: If any config file doesn't exist
        """
        hasher = hashlib.sha256()

        # Sort by key for consistent ordering
        for key in sorted(config_files.keys()):
            path = config_files[key]
            if not path.exists():
                raise FileNotFoundError(f"Config file not found: {path}")

            # Read file and hash content
            with open(path, "rb") as f:
                hasher.update(f.read())

        return hasher.hexdigest()
