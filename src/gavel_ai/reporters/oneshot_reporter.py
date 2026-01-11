"""
OneShot report generator.

Generates reports for OneShot evaluations with winner indication,
judge reasoning, and detailed results per scenario.
"""

from typing import Any, Dict, List

from gavel_ai.models.runtime import ReporterConfig
from gavel_ai.reporters.jinja_reporter import Jinja2Reporter


class OneShotReporter(Jinja2Reporter):
    """
    OneShot-specific report generator.

    Extends Jinja2Reporter to add OneShot-specific features:
    - Winner calculation based on total scores
    - Judge list extraction
    - Enhanced context formatting

    Per Architecture Decision 8: Pluggable report formats with clean abstraction.
    """

    def __init__(self, config: ReporterConfig):
        """
        Initialize OneShotReporter with configuration.

        Args:
            config: ReporterConfig with template_path and output_format
        """
        super().__init__(config)

    def _build_context(self, run: Any) -> Dict[str, Any]:
        """
        Build context dictionary for OneShot template rendering.

        Extends parent _build_context() with OneShot-specific data:
        - winner: Winning variant based on total scores
        - judges: List of unique judges used in evaluation
        - performance: Performance metrics from run metadata (timing, tokens, etc.)

        Args:
            run: Run instance with metadata, results, and telemetry

        Returns:
            Dict[str, Any]: Context dictionary with template variables
        """
        # Get base context from parent
        context = super()._build_context(run)

        # Add OneShot-specific context
        context["winner"] = self._calculate_winner(context["summary"])
        context["judges"] = self._extract_judges_list(run)
        context["performance"] = self._extract_performance_metrics(run)

        return context

    def _calculate_winner(self, summary: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate winning variant based on total scores.

        Args:
            summary: Summary table with variant scores

        Returns:
            Dict[str, Any]: Winner information with variant_id, total_score, avg_score, is_tie
        """
        if not summary:
            return {
                "variant_id": "N/A",
                "total_score": 0,
                "avg_score": 0,
                "is_tie": False,
            }

        # Sort by total score descending
        sorted_summary = sorted(summary, key=lambda x: x["total_score"], reverse=True)

        winner = sorted_summary[0]

        # Check for tie: multiple variants with same top score
        top_score = winner["total_score"]
        tied_variants = [v for v in sorted_summary if v["total_score"] == top_score]
        is_tie = len(tied_variants) > 1

        return {
            "variant_id": winner["variant_id"],
            "total_score": winner["total_score"],
            "avg_score": winner["avg_score"],
            "is_tie": is_tie,
        }

    def _extract_judges_list(self, run: Any) -> List[Dict[str, str]]:
        """
        Extract unique judges from results.

        Args:
            run: Run instance with results

        Returns:
            List[Dict[str, str]]: List of judges with judge_id and judge_name
        """
        results = getattr(run, "results", [])

        if not results:
            return []

        # Collect unique judge IDs
        judge_ids = set()
        judges = []

        for result in results:
            result_judges = result.get("judges", [])
            for judge in result_judges:
                judge_id = judge.get("judge_id", "unknown")
                if judge_id not in judge_ids:
                    judge_ids.add(judge_id)
                    judges.append(
                        {
                            "judge_id": judge_id,
                            "judge_name": judge_id,  # For now, name == id
                        }
                    )

        return judges

    def _extract_performance_metrics(self, run: Any) -> Dict[str, Any]:
        """
        Extract performance metrics from run metadata (Story 7.2).

        Args:
            run: Run instance with metadata

        Returns:
            Dict[str, Any]: Performance metrics for template rendering
        """
        import json
        from pathlib import Path

        # Try to load run_metadata.json if it exists
        try:
            # Check if run has run_dir attribute (LocalFilesystemRun)
            run_dir = getattr(run, "run_dir", None)
            if run_dir:
                metadata_file = Path(run_dir) / "run_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata_data = json.load(f)
                    return {
                        "has_metrics": True,
                        "total_duration_seconds": metadata_data.get("total_duration_seconds", 0),
                        "scenario_timing": metadata_data.get("scenario_timing", {}),
                        "llm_calls": metadata_data.get("llm_calls", {}),
                        "execution": metadata_data.get("execution", {}),
                    }
        except Exception:
            # If metadata file not found or parsing fails, continue with empty metrics
            pass

        # Return empty metrics structure if not found
        return {
            "has_metrics": False,
            "total_duration_seconds": 0,
            "scenario_timing": {},
            "llm_calls": {},
            "execution": {},
        }
